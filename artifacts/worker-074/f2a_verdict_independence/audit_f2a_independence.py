#!/usr/bin/env python3
"""W074-A1-INDEP-01: independence audit of the F2a (AF-SCC-C2-VAC-GEN) review corpus.

Question (G-FORM criterion, PROTOCOL.md rule and audit-rubric duplication metric):
  the gate needs TWO INDEPENDENT accept verdicts at the measured canonical hash.
  The controller counts DISTINCT REVIEWER IDS.  The protocol says two reviews that
  agree because they share a text/template count as ONE.  This instrument closes that
  gap for F2a: it measures, for every review verdict that binds the measured hash,
  whether it is independent of the others by reviewer identity, by verdict text, and
  by evidence channel.

Deterministic; no network; fails closed on input drift. Read-only with respect to
all canonical artifacts. Worker evidence only: issues no gate verdict, sets no node
status, edits no canonical path.

Run:  python3 artifacts/worker-074/f2a_verdict_independence/audit_f2a_independence.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT_DIR = Path(__file__).resolve().parent

# --- pinned target -----------------------------------------------------------
TARGET_PATH = "schemas/af_scc_c2_vacuum.yaml"
TARGET_CLASS = "AF-SCC-C2-VAC-GEN"
TARGET_NODE = "F2a"
EXPECTED_SHA256 = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
HASH_PREFIX = EXPECTED_SHA256[:12]

# similarity thresholds; primary text-cluster threshold is INDEP_THRESHOLD
SHINGLE_N = 6
INDEP_THRESHOLD = 0.60
SENSITIVITY = [0.50, 0.60, 0.70, 0.80]

# Artifacts every F2a review is *expected* to consume; sharing them is not an
# independent evidence channel.  A review's "own evidence" is everything else.
SHARED_BASELINE = {
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "research_map/formulation_taxonomy.yaml",
    "research_map/research_map.json",
    "artifacts/formulation/tools/check_class_schema.py",
    "research_map/class_separation.py",
    "runtime/bin/classsep_regression.py",
    "evaluation_rubric.yaml",
}
# target tokens that bind a review to F2a
F2A_TARGETS = {"f2a", "af-scc-c2-vac-gen", "schemas/af_scc_c2_vacuum.yaml", "f1,f2a,f2b", "f2a,f2b", "f2"}
OTHER_SINGLE_TARGETS = {"f0", "f2b", "l0", "l1", "n0", "n1", "a0", "a1", "a2"}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def get_json_objects(path: Path):
    """Tolerant extraction, same shapes the comms bus accepts."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return
    text = text.strip()
    if not text:
        return
    try:
        doc = json.loads(text)
        if isinstance(doc, dict):
            yield doc
        elif isinstance(doc, list):
            for d in doc:
                if isinstance(d, dict):
                    yield d
        return
    except ValueError:
        pass
    for block in re.findall(r"```(?:json)?\s*(.*?)```", text, re.S):
        try:
            doc = json.loads(block.strip())
        except ValueError:
            continue
        if isinstance(doc, dict):
            yield doc
        elif isinstance(doc, list):
            for d in doc:
                if isinstance(d, dict):
                    yield d
    for line in text.splitlines():
        line = line.strip().rstrip(",")
        if line.startswith("{") and line.endswith("}"):
            try:
                yield json.loads(line)
            except ValueError:
                pass


def harvest_events():
    by_id: dict[str, dict] = {}
    paths = [ROOT / "research_map" / "events.jsonl"]
    paths += sorted(Path(p) for p in glob.glob(str(ROOT / "comms" / "outbox" / "**" / "*.jsonl"), recursive=True))
    paths += sorted(Path(p) for p in glob.glob(str(ROOT / "comms" / "outbox" / "**" / "*.json"), recursive=True))
    files = []
    for p in paths:
        if not p.is_file():
            continue
        files.append({"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p)})
        for obj in get_json_objects(p) or []:
            eid = obj.get("event_id")
            if not eid:
                continue
            prev = by_id.get(eid)
            if prev is None or len(json.dumps(obj, sort_keys=True)) >= len(json.dumps(prev, sort_keys=True)):
                by_id[eid] = obj
    return by_id, files


def target_tokens(e: dict):
    tid = e.get("target_id") or e.get("node_id") or ""
    toks = []
    for t in re.split(r"[,;]", str(tid)):
        t = t.strip().lower()
        t = re.sub(r"#.*$", "", t)  # strip #sha256 / #anchor suffixes
        if t:
            toks.append(t)
    return toks


def doc_paths(e: dict):
    cands = []
    for k in ("review_path", "artifact", "artifact_path", "target_artifact", "report_path"):
        v = e.get(k)
        if isinstance(v, str) and v.endswith((".json", ".md")):
            cands.append(v)
    for k in ("artifact_refs", "evidence_refs"):
        v = e.get(k)
        if isinstance(v, list):
            for x in v:
                if isinstance(x, str):
                    p = x.split("#")[0].split(":")[0].strip()
                    if p.endswith((".json", ".md")) and any(t in p.lower() for t in ("review", "verdict", "report", "evidence", "audit", "check")):
                        cands.append(p)
    seen, out = set(), []
    for c in cands:
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def extract_hash_fields(obj, acc=None, depth=0):
    if acc is None:
        acc = set()
    if depth > 6:
        return acc
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{12,64}", v.lower()):
                acc.add(v.lower())
            else:
                extract_hash_fields(v, acc, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            extract_hash_fields(v, acc, depth + 1)
    return acc


def findings_text(e: dict) -> str:
    f = e.get("findings")
    if f is None:
        f = e.get("summary") or ""
    return json.dumps(f, ensure_ascii=False, sort_keys=True) if not isinstance(f, str) else f


def is_f2a_scoped(e: dict, doc_path: str | None) -> tuple[bool, str]:
    toks = target_tokens(e)
    if any(t in F2A_TARGETS for t in toks):
        return True, "target_id"
    if doc_path and re.search(r"(^|[/_-])f2a", doc_path.lower()):
        return True, "review_doc_path"
    # multi-target events listing F2a among tokens
    if toks and all(t in OTHER_SINGLE_TARGETS or t == "f2a" for t in toks) and "f2a" in toks:
        return True, "target_id_multi"
    return False, "out_of_scope"


def load_doc_text(paths):
    for rel in paths:
        p = ROOT / rel
        if p.is_file():
            try:
                raw = p.read_text(errors="replace")
            except OSError:
                continue
            doc_hashes = set()
            try:
                doc_hashes = extract_hash_fields(json.loads(raw))
            except ValueError:
                pass
            return raw, rel, doc_hashes, sha256_text(raw)
    return "", None, set(), None


def tokens(text: str):
    return re.findall(r"[a-z0-9_]+", text.lower())


def shingles(text: str, n: int = SHINGLE_N):
    t = tokens(text)
    if len(t) < n:
        return {" ".join(t)} if t else set()
    return {" ".join(t[i : i + n]) for i in range(len(t) - n + 1)}


class DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def cluster(n, pair_pred):
    d = DSU(n) if n else None
    for i in range(n):
        for j in range(i + 1, n):
            if pair_pred(i, j) and d is not None:
                d.union(i, j)
    groups: dict[int, list[int]] = {}
    if n:
        for i in range(n):
            groups.setdefault(d.find(i), []).append(i)
    return d, groups


def main():
    started = now()
    target = ROOT / TARGET_PATH
    if not target.is_file():
        print(json.dumps({"error": f"missing {TARGET_PATH}"}))
        return 2
    measured = sha256_file(target)
    target_bytes = target.stat().st_size

    events, source_files = harvest_events()
    cutoff = max((str(e.get("created_at") or "") for e in events.values()), default="")
    corpus_ids = sorted(eid for eid, e in events.items() if e.get("event_type") == "review")
    corpus_digest = hashlib.sha256("\n".join(corpus_ids).encode()).hexdigest()

    rows, excluded = [], []
    for eid, e in events.items():
        if e.get("event_type") != "review":
            continue
        paths = doc_paths(e)
        text, path_used, doc_hashes, doc_sha = load_doc_text(paths)
        scoped, why = is_f2a_scoped(e, path_used)
        hashes = set(doc_hashes)
        extract_hash_fields(e, hashes)
        blob = json.dumps(e, sort_keys=True, ensure_ascii=False)
        binds = HASH_PREFIX in blob or any(h.startswith(HASH_PREFIX) for h in hashes)
        if not scoped:
            excluded.append({"event_id": eid, "reason": f"{why}: target_id={e.get('target_id')}", "verdict": e.get("verdict")})
            continue
        evidence = []
        for k in ("evidence_refs", "artifact_refs", "reviewed_artifacts"):
            v = e.get(k)
            if isinstance(v, list):
                evidence += [x for x in v if isinstance(x, str)]
            elif isinstance(v, dict):
                evidence += list(v.keys())
        ev_paths = sorted({x.split("#")[0].strip() for x in evidence if isinstance(x, str)})
        # own evidence = cited inputs minus (a) the shared baseline every F2a review
        # must consume and (b) the reviewer's own verdict document (self-reference).
        # Reviewer-specific instruments/outputs are KEPT: they are the independent channel.
        own_evidence = sorted(p for p in ev_paths if p not in SHARED_BASELINE and p != path_used)
        rows.append(
            {
                "event_id": eid,
                "created_at": e.get("created_at"),
                "reviewer": e.get("reviewer") or e.get("actor"),
                "actor": e.get("actor"),
                "verdict": e.get("verdict"),
                "score": e.get("score"),
                "target_id": e.get("target_id"),
                "scope_reason": why,
                "binds_expected_hash": bool(binds),
                "review_doc": path_used,
                "review_doc_sha256": doc_sha,
                "findings_text": findings_text(e) or text,
                "evidence_paths": ev_paths,
                "own_evidence_paths": own_evidence,
                "hard_failures": e.get("hard_failures"),
            }
        )

    bound = sorted([r for r in rows if r["binds_expected_hash"]], key=lambda r: (str(r["created_at"]), r["event_id"]))
    n = len(bound)

    # --- 1. reviewer-identity dedup (same reviewer at the same target is one verdict)
    by_reviewer: dict[str, list[int]] = {}
    for i, r in enumerate(bound):
        by_reviewer.setdefault(str(r["reviewer"]), []).append(i)
    reviewer_dup = {k: v for k, v in by_reviewer.items() if len(v) > 1}

    # --- 2. text clustering
    def text_dup(i, j):
        a, b = bound[i], bound[j]
        if a["review_doc_sha256"] and a["review_doc_sha256"] == b["review_doc_sha256"]:
            return True
        return jaccard(shingles(a["findings_text"]), shingles(b["findings_text"])) >= INDEP_THRESHOLD

    _, text_groups = cluster(n, text_dup)

    # --- 3. full independence: same reviewer OR text duplicate
    def full_dup(i, j):
        return str(bound[i]["reviewer"]) == str(bound[j]["reviewer"]) or text_dup(i, j)

    _, full_groups = cluster(n, full_dup)

    # --- 4. evidence channels among accepts: own evidence set identity; empty own
    #        evidence = shared canonical-gate channel
    accepts = [i for i in range(n) if bound[i]["verdict"] == "accept"]
    ev_key = {}
    for i in accepts:
        own = tuple(bound[i]["own_evidence_paths"])
        ev_key[i] = own if own else ("<shared-canonical-gate-only>",)
    ev_groups: dict[tuple, list[int]] = {}
    for i in accepts:
        ev_groups.setdefault(ev_key[i], []).append(i)

    def summarize(groups, verdict_filter=None):
        out = []
        for _k, idxs in sorted(groups.items(), key=lambda kv: min(kv[1])):
            members = [bound[i] for i in idxs]
            members.sort(key=lambda r: (str(r["created_at"]), r["event_id"]))
            if verdict_filter and not any(m["verdict"] == verdict_filter for m in members):
                continue
            out.append(
                {
                    "size": len(members),
                    "verdicts": sorted({str(m["verdict"]) for m in members}),
                    "representative_reviewer": members[0]["reviewer"],
                    "member_reviewers": sorted({str(m["reviewer"]) for m in members}),
                    "members": [m["event_id"] for m in members],
                }
            )
        out.sort(key=lambda c: (c["representative_reviewer"], c["members"][0]))
        return out

    text_clusters = summarize(text_groups)
    full_clusters = summarize(full_groups)
    eff_accept = [c for c in full_clusters if "accept" in c["verdicts"]]
    eff_revise = [c for c in full_clusters if "revise" in c["verdicts"]]
    eff_inconc = [c for c in full_clusters if "inconclusive" in c["verdicts"]]
    ev_accept_channels = [{"own_evidence": list(k), "members": [bound[i]["event_id"] for i in v], "reviewers": sorted({str(bound[i]["reviewer"]) for i in v})} for k, v in sorted(ev_groups.items(), key=lambda kv: min(kv[1]))]

    sensitivity = {}
    for th in SENSITIVITY:
        def pred(i, j, th=th):
            a, b = bound[i], bound[j]
            if str(a["reviewer"]) == str(b["reviewer"]):
                return True
            if a["review_doc_sha256"] and a["review_doc_sha256"] == b["review_doc_sha256"]:
                return True
            return jaccard(shingles(a["findings_text"]), shingles(b["findings_text"])) >= th

        _, g = cluster(n, pred)
        acc = [k for k, v in g.items() if any(bound[i]["verdict"] == "accept" for i in v)]
        sensitivity[str(th)] = {"clusters_total": len(g), "effective_accepts": len(acc)}

    measured_after = sha256_file(target)
    drift = measured_after != measured

    report = {
        "schema_version": "1.0",
        "artifact_type": "a1_review_independence_audit",
        "artifact_id": "artifacts/worker-074/f2a_verdict_independence/audit_report.json",
        "task_id": "W074-A1-INDEP-01",
        "actor": "worker-074",
        "created_at": started,
        "created_at_basis": "wall clock at write time (CF-14 clock discipline)",
        "authority": "worker evidence only; no gate verdict, no node status, no review verdict, no canonical-file edit",
        "not_duplicative_of": [
            "controller_gate_audit (counts distinct reviewer ids only; does not measure text/template sharing or evidence channels)",
            "artifacts/worker-057/xdata_check (data-class sharing, not review independence)",
            "individual F2a reviews (worker-047, -050, -061, -069, -072, -078, -098, deepseek-flash-15/20/21/22/33/88/95/86): this audit consumes their recorded verdicts and re-issues none",
        ],
        "question": (
            "How many of the recorded F2a review verdicts that bind the measured canonical hash are "
            "mutually independent under the protocol rule 'two reviews that agree because they are the "
            "same text count as one' (Kish-ESS-style dedup), and does the G-FORM 'two independent "
            "accepts' criterion hold after dedup?"
        ),
        "target": {
            "path": TARGET_PATH,
            "class_id": TARGET_CLASS,
            "node_id": TARGET_NODE,
            "gate": "G-FORM",
            "expected_sha256": EXPECTED_SHA256,
            "measured_sha256_at_start": measured,
            "measured_sha256_at_end": measured_after,
            "bytes": target_bytes,
            "drift_during_run": drift,
            "hash_stable": not drift,
        },
        "method": {
            "event_harvest": "research_map/events.jsonl + every comms/outbox/**/*.jsonl and *.json, dedup by event_id (richer copy wins)",
            "scope_rule": "target_id token in {F2a, AF-SCC-C2-VAC-GEN, schemas/af_scc_c2_vacuum.yaml, F1,F2a,F2b, F2a,F2b, F2} or review-doc path matching f2a; other single-node targets excluded",
            "binding_rule": f"current-hash-bound iff prefix {HASH_PREFIX} appears in the event or any sha256 field of an on-disk review document it names",
            "reviewer_dedup": "one verdict per reviewer id per target hash; duplicates counted once (the later event is the representative)",
            "text_similarity": f"token {SHINGLE_N}-gram Jaccard on the reviewer's own findings text; identical normalized review-document sha256 is an automatic duplicate",
            "text_cluster_threshold": INDEP_THRESHOLD,
            "sensitivity_thresholds": SENSITIVITY,
            "evidence_channel": f"own evidence = cited paths minus the shared baseline (canonical schema/taxonomy/rule-spec/checkers/FROZEN) and minus the reviewer's own verdict document; reviewer-specific instruments and probe outputs count as that reviewer's channel. Accepts with an empty own-evidence set form one shared-canonical-gate-only channel.",
            "limits": [
                "Some events name no on-disk review document; their findings were reconstructed from the event JSON, which can understate similarity if a shared template was trimmed differently.",
                "This audit measures independence of verdicts, NOT their correctness; a genuine independent accept can still be wrong.",
                "The corpus is a growing snapshot: pinned by recorded cutoff time, review-event count and event-id digest; later verdicts are not included.",
            ],
        },
        "sources": {"events_and_outboxes": source_files, "n_source_files": len(source_files)},
        "corpus": {
            "snapshot_created_at": started,
            "latest_event_created_at_seen": cutoff,
            "review_events_seen_total": len(corpus_ids),
            "review_events_corpus_digest_sha256": corpus_digest,
            "f2a_scoped_review_events": len(rows),
            "out_of_scope_reviews_excluded": len(excluded),
            "bound_to_measured_hash": n,
            "verdict_counts_bound": {
                "accept": len(accepts),
                "revise": sum(1 for r in bound if r["verdict"] == "revise"),
                "inconclusive": sum(1 for r in bound if r["verdict"] == "inconclusive"),
            },
            "distinct_reviewer_ids_bound": sorted(by_reviewer),
            "reviewers_with_duplicate_verdicts": {k: [bound[i]["event_id"] for i in v] for k, v in reviewer_dup.items()},
            "raw_accept_count": len(accepts),
            "raw_accept_reviewers": sorted({str(bound[i]["reviewer"]) for i in accepts}),
            "effective_independent_accept_count_identity_and_text": len(eff_accept),
            "effective_independent_accept_count_evidence_channels": len(ev_accept_channels),
            "accepts_with_no_own_evidence_shared_gate_only": sum(1 for i in accepts if not bound[i]["own_evidence_paths"]),
            "effective_independent_revise_count": len(eff_revise),
            "effective_independent_inconclusive_count": len(eff_inconc),
            "sensitivity": sensitivity,
        },
        "clusters": {
            "identity_and_text": full_clusters,
            "text_only": text_clusters,
            "accept_evidence_channels": ev_accept_channels,
        },
        "rows": rows,
        "excluded": excluded,
        "finding": {
            "id": "W074-INDEP-F1",
            "severity": "info" if len(eff_accept) >= 2 else "blocking-for-criterion",
            "statement": (
                f"At {TARGET_PATH}#{HASH_PREFIX} the snapshot holds {len(accepts)} accept verdict(s) from "
                f"{len({str(bound[i]['reviewer']) for i in accepts})} distinct reviewer id(s); after reviewer-identity and "
                f"text dedup they remain {len(eff_accept)} independent accept cluster(s), carried by "
                f"{len(ev_accept_channels)} distinct evidence-channel signature(s). "
                f"{sum(1 for i in accepts if not bound[i]['own_evidence_paths'])} accept(s) cite no reviewer-specific "
                f"instrument/output beyond the shared canonical gate."
            ),
            "criterion_gform_two_independent_accepts": "met at this snapshot" if len(eff_accept) >= 2 else "not met at this snapshot",
            "effective_accept_clusters": eff_accept,
            "accept_evidence_channels": ev_accept_channels,
            "caveat": (
                "Independence is necessary, not sufficient, for the G-FORM criterion: the criterion also requires "
                "the accepts to be correct and at the frozen hash. This audit does not re-adjudicate correctness."
            ),
        },
        "falsifier": (
            "FALSIFIED IF: (a) the measured sha256 of %s is not %s when re-run, or it drifts during the run; "
            "(b) re-running this script on the same recorded corpus yields different cluster assignments; "
            "(c) any two reviews placed in one identity/text cluster belong to different reviewers with distinct "
            "review-document sha256 and findings shingle-Jaccard < %s; or (d) any review counted as an independent "
            "accept is shown to be a re-send of another reviewer's text or a template whose decisive evidence is "
            "the same single artifact as another accept's."
        ) % (TARGET_PATH, EXPECTED_SHA256, INDEP_THRESHOLD),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "audit_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (OUT_DIR / "snapshot_row_ids.json").write_text(
        json.dumps({"cutoff": cutoff, "n_reviews_seen": len(corpus_ids), "digest": corpus_digest, "bound_event_ids": [r["event_id"] for r in bound]}, indent=2) + "\n"
    )

    summary = {
        "report": str(out.relative_to(ROOT)),
        "report_sha256": sha256_file(out),
        "target_sha256": measured,
        "scoped_reviews": len(rows),
        "bound_reviews": n,
        "raw_accepts": len(accepts),
        "effective_independent_accepts_identity_text": len(eff_accept),
        "effective_accept_evidence_channels": len(ev_accept_channels),
        "criterion": report["finding"]["criterion_gform_two_independent_accepts"],
        "drift": drift,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
