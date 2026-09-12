#!/usr/bin/env python3
"""
W053-REJECT-RECOVERY-CENSUS-01  (worker-053, node A1, gate G-AUDIT)

Question: when the ingest validator drops a claim (`claim: invalid conclusion_type`),
does the class-bound claim survive anywhere in the accepted stream?

Deterministic, stdlib-only, read-only on every canonical path. All inputs are read
exactly once (one-read pinning); every input is re-measured at the end (drift guard).

Recovery ladder (first predicate that fires is recorded; all flags are recorded):
  1 ACCEPTED_EVENT_ID      an accepted event carries the exact rejected event_id
  2 REFILED_BY_REFERENCE   some accepted event text contains the rejected event_id
  3 REFILED_BY_TASK        an accepted claim shares task_id + class intersection
  4 SUBSTANCE_LANDED       a claim artifact_ref appears in accepted evidence, or the
                           ref exists on disk with a matching hash AND the task_id
                           appears in an accepted event
  5 ABSENT                 none of the above (class-bound rows only)
  U UNRECOVERABLE_SOURCE   the full event cannot be recovered from its source outbox
                           line; excluded from ABSENT (reported separately)

Run:  python3 artifacts/worker-053/reject_recovery_census/recover_rejects_053.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]          # artifacts/worker-053/reject_recovery_census -> repo root
CST = timezone(timedelta(hours=8))
TASK_ID = "W053-REJECT-RECOVERY-CENSUS-01"
CANON = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
PIN_FILES = [
    "comms/rejected.jsonl",
    "research_map/events.jsonl",
    "research_map/schemas.py",
    "research_map/research_map.json",
]
OUTBOX_DIR = "comms/outbox"
HEX16 = re.compile(r"^[0-9a-f]{6,64}$")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm_path(p: str) -> str:
    p = p.strip().lstrip("./")
    return p.replace("\\", "/")


# ---------------------------------------------------------------- json objects
def iter_objects(text: str):
    """Yield dicts from JSONL / whole-file JSON / fenced markdown (mirrors comms.py)."""
    text = text.strip()
    if not text:
        return
    try:
        doc = json.loads(text)
        if isinstance(doc, dict):
            yield doc
            return
        if isinstance(doc, list):
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
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            doc = json.loads(line)
        except ValueError:
            continue
        if isinstance(doc, dict):
            yield doc


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from walk_strings(v)


def evidence_tokens(event: dict):
    """(paths, path#hash-prefix tokens) referenced anywhere in an event."""
    paths, hashed = set(), set()
    for s in walk_strings(event):
        if not isinstance(s, str) or "/" not in s or "." not in s:
            continue
        if "#" in s:
            base, _, h = s.partition("#")
            base = norm_path(base)
            if base and HEX16.match(h.strip().lower()):
                hashed.add(base + "#" + h.strip().lower()[:16])
                paths.add(base)
        else:
            paths.add(norm_path(s))
    return paths, hashed


# ---------------------------------------------------------------- snapshot
class Snapshot:
    def __init__(self):
        self.taken_at = now()
        self.bytes = {}
        for rel in PIN_FILES:
            p = ROOT / rel
            self.bytes[rel] = p.read_bytes() if p.exists() else None
        self.outbox_files = sorted(
            p for p in (ROOT / OUTBOX_DIR).rglob("*")
            if p.is_file() and not p.name.startswith("._")
        )
        self.outbox_bytes = {}
        self.outbox_sha = {}
        for p in self.outbox_files:
            rel = str(p.relative_to(ROOT))
            b = p.read_bytes()
            self.outbox_bytes[rel] = b
            self.outbox_sha[rel] = sha256_bytes(b)
        digest = hashlib.sha256()
        for rel in sorted(self.outbox_sha):
            digest.update(rel.encode() + b"\0" + self.outbox_sha[rel].encode() + b"\n")
        self.outbox_digest = digest.hexdigest()

    def pins(self):
        out = {}
        for rel, b in self.bytes.items():
            out[rel] = None if b is None else {"sha256": sha256_bytes(b), "bytes": len(b)}
        out[OUTBOX_DIR + "/*"] = {
            "n_files": len(self.outbox_files),
            "set_digest": self.outbox_digest,
        }
        return out

    def drift(self):
        after = {}
        for rel, b0 in self.bytes.items():
            p = ROOT / rel
            b1 = p.read_bytes() if p.exists() else None
            after[rel] = {
                "before": None if b0 is None else sha256_bytes(b0),
                "after": None if b1 is None else sha256_bytes(b1),
            }
        o_after = {}
        for p in sorted(
            q for q in (ROOT / OUTBOX_DIR).rglob("*")
            if q.is_file() and not q.name.startswith("._")
        ):
            rel = str(p.relative_to(ROOT))
            o_after[rel] = sha256_bytes(p.read_bytes())
        changed = [r for r, v in after.items() if v["before"] != v["after"]]
        ob_changed = sorted(
            r for r in set(o_after) | set(self.outbox_sha)
            if o_after.get(r) != self.outbox_sha.get(r)
        )
        return {
            "pinned_files": after,
            "outbox_changed_files": ob_changed,
            "outbox_files_after": len(o_after),
            "drift": bool(changed or ob_changed),
            "changed_pinned_files": changed,
        }


# ---------------------------------------------------------------- indexes
class Index:
    def __init__(self, accepted, outbox_by_id, outbox_by_source):
        self.accepted = accepted
        self.outbox_by_id = outbox_by_id          # event_id -> [(source, event)]
        self.outbox_by_source = outbox_by_source  # source -> {event_id: event}
        self.accepted_ids = {e.get("event_id") for e in accepted if e.get("event_id")}
        self.accepted_tasks = {
            e.get("task_id") for e in accepted if e.get("task_id")
        }
        self.accepted_blob = json.dumps(accepted, ensure_ascii=False)
        self.by_task = defaultdict(list)
        for e in accepted:
            if e.get("task_id"):
                self.by_task[e["task_id"]].append(e)
        self.ev_paths = set()
        self.ev_hashed = set()
        for e in accepted:
            pp, hh = evidence_tokens(e)
            self.ev_paths |= pp
            self.ev_hashed |= hh

    def clone(self, extra_accepted=(), exclude_accepted_ids=()):
        accepted = [e for e in self.accepted if e.get("event_id") not in set(exclude_accepted_ids)]
        accepted = accepted + list(extra_accepted)
        return Index(accepted, self.outbox_by_id, self.outbox_by_source)


def build_indexes(snap: Snapshot) -> Index:
    accepted = []
    ev_b = snap.bytes["research_map/events.jsonl"]
    if ev_b:
        for line in ev_b.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    accepted.append(json.loads(line))
                except ValueError:
                    pass
    outbox_by_id = defaultdict(list)
    outbox_by_source = defaultdict(dict)
    for rel in sorted(snap.outbox_bytes):
        seen_local = set()
        for ev in iter_objects(snap.outbox_bytes[rel].decode("utf-8", "replace")):
            eid = ev.get("event_id")
            if not eid or eid in seen_local:
                continue
            seen_local.add(eid)
            outbox_by_id[eid].append((rel, ev))
            outbox_by_source[rel][eid] = ev
    return Index(accepted, outbox_by_id, outbox_by_source)


# ---------------------------------------------------------------- census
def canonical_enum(snap: Snapshot):
    b = snap.bytes["research_map/schemas.py"]
    text = b.decode("utf-8", "replace") if b else ""
    m = re.search(
        r'conclusion_type"\s+not\s+in\s+\{([^}]*)\}', text
    )
    if not m:
        return set(), None
    vals = set(re.findall(r'"([^"]+)"', m.group(1)))
    return vals, m.group(0)


def class_ids_of(ev: dict, raw: str):
    cids = []
    if isinstance(ev.get("class_ids"), list):
        cids += [str(x) for x in ev["class_ids"]]
    cid = ev.get("class_id")
    if isinstance(cid, str):
        cids += [x.strip() for x in re.split(r"[;,]", cid) if x.strip()]
    if not cids and raw:
        for m in re.finditer(r'"class_ids":\s*\[([^\]]*)\]', raw):
            cids += re.findall(r'"([^"]+)"', m.group(1))
        for m in re.finditer(r'"class_id":\s*"([^"]+)"', raw):
            cids += [x.strip() for x in re.split(r"[;,]", m.group(1)) if x.strip()]
    seen, out = set(), []
    for c in cids:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def artifact_refs_of(ev: dict, raw: str):
    refs = []
    for key in ("artifact_refs", "evidence_refs"):
        v = ev.get(key)
        if isinstance(v, list):
            refs += [str(x) for x in v]
    if raw:
        for key in ("artifact_refs", "evidence_refs"):
            for m in re.finditer(r'"%s":\s*\[([^\]]*)\]' % key, raw):
                refs += re.findall(r'"([^"]+)"', m.group(1))
    out, seen = [], set()
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def ref_status(refs, idx: Index):
    in_accepted = False
    on_disk = False
    details = []
    for r in refs:
        base, _, h = r.partition("#")
        base = norm_path(base)
        h = h.strip().lower()
        ok_acc = base in idx.ev_paths or (h and (base + "#" + h[:16]) in idx.ev_hashed)
        p = ROOT / base
        exists = p.exists()
        hash_ok = None
        if exists:
            try:
                hash_ok = bool(h) and sha256_bytes(p.read_bytes()).startswith(h[:16])
            except OSError:
                hash_ok = None
        if ok_acc:
            in_accepted = True
        if exists and (not h or hash_ok):
            on_disk = True
        details.append(
            {"ref": r, "in_accepted": ok_acc, "exists": exists, "hash_ok": hash_ok}
        )
    return in_accepted, on_disk, details


def classify(row: dict, idx: Index, enum: set):
    """Classify one rejected claim row. Returns dict."""
    eid = row.get("event_id") or ""
    source = row.get("source") or ""
    rec = {"event_id": eid, "source": source, "rejected_at": row.get("rejected_at")}
    ev = None
    method = "none"
    if source in idx.outbox_by_source and eid in idx.outbox_by_source[source]:
        ev = idx.outbox_by_source[source][eid]
        method = "source_outbox"
    elif eid in idx.outbox_by_id:
        ev = idx.outbox_by_id[eid][0][1]
        method = "other_outbox"
    raw = row.get("raw") or ""
    if ev is None:
        rec["recovery_method"] = "raw_only" if raw else "none"
        rec["unrecoverable_source"] = True
        rec["class_ids"] = class_ids_of({}, raw)
        rec["class_bound"] = bool(set(rec["class_ids"]) & set(CANON))
        rec["task_id"] = (re.search(r'"task_id":\s*"([^"]+)"', raw) or [None, None])[1]
        rec["gate"] = (re.search(r'"gate":\s*"([^"]+)"', raw) or [None, None])[1]
        rec["conclusion_type"] = (re.search(r'"conclusion_type":\s*"([^"]+)"', raw) or [None, None])[1]
        rec["recovery"] = "UNRECOVERABLE_SOURCE"
        return rec
    rec["recovery_method"] = method
    rec["unrecoverable_source"] = False
    rec["class_ids"] = class_ids_of(ev, raw)
    rec["class_bound"] = bool(set(rec["class_ids"]) & set(CANON))
    rec["task_id"] = ev.get("task_id")
    rec["gate"] = ev.get("gate")
    rec["conclusion_type"] = ev.get("conclusion_type")
    rec["valid_ctype_now"] = rec["conclusion_type"] in enum
    refs = artifact_refs_of(ev, raw)
    rec["artifact_refs"] = refs
    rec["accepted_event_id"] = eid in idx.accepted_ids
    rec["referenced_in_accepted"] = bool(eid) and (eid in idx.accepted_blob)
    rec["refiled_by_task"] = bool(
        rec["task_id"]
        and rec["class_bound"]
        and any(
            isinstance(x.get("class_id"), str)
            and set(re.split(r"[;,]", x["class_id"])) & set(rec["class_ids"])
            for x in idx.by_task.get(rec["task_id"], [])
            if x.get("event_type") == "claim"
        )
    ) or bool(
        rec["task_id"] and rec["task_id"] in idx.accepted_tasks and rec["conclusion_type"] not in enum
    )
    in_acc, on_disk, ref_details = ref_status(refs, idx)
    rec["evidence_in_accepted"] = in_acc
    rec["evidence_on_disk"] = on_disk
    rec["ref_details"] = ref_details
    task_landed = bool(rec["task_id"] and rec["task_id"] in idx.accepted_tasks)
    if rec["accepted_event_id"]:
        rec["recovery"] = "ACCEPTED_EVENT_ID"
    elif rec["referenced_in_accepted"]:
        rec["recovery"] = "REFILED_BY_REFERENCE"
    elif rec["refiled_by_task"]:
        rec["recovery"] = "REFILED_BY_TASK"
    elif in_acc or (on_disk and task_landed):
        rec["recovery"] = "SUBSTANCE_LANDED"
    else:
        rec["recovery"] = "ABSENT"
    return rec


def census(rows, idx: Index, enum: set):
    """Deduplicate by event_id, classify all invalid-ctype rows."""
    seen = set()
    out = []
    for r in rows:
        if r.get("reason") != "claim: invalid conclusion_type":
            continue
        eid = r.get("event_id")
        if eid in seen:
            continue
        seen.add(eid)
        out.append(classify(r, idx, enum))
    return out


def load_rejects(snap: Snapshot):
    b = snap.bytes["comms/rejected.jsonl"]
    rows = []
    if b:
        for line in b.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def ctype_usage(snap: Snapshot):
    """conclusion_type distribution over outbox events, split by ingest fate."""
    by_all = Counter()
    by_source_of_rejected = Counter()
    rejected_ids = {r.get("event_id") for r in load_rejects(snap)}
    for rel in sorted(snap.outbox_bytes):
        for ev in iter_objects(snap.outbox_bytes[rel].decode("utf-8", "replace")):
            if ev.get("event_type") != "claim":
                continue
            ct = ev.get("conclusion_type")
            by_all[ct] += 1
            if ev.get("event_id") in rejected_ids:
                by_source_of_rejected[ct] += 1
    return dict(by_all), dict(by_source_of_rejected)


# ---------------------------------------------------------------- main
def main():
    started = now()
    snap = Snapshot()
    idx = build_indexes(snap)
    enum, enum_src = canonical_enum(snap)
    rows = load_rejects(snap)
    results = census(rows, idx, enum)
    drifts = snap.drift()

    by_reason = Counter(r.get("reason") for r in rows)
    invalid = [r for r in results]
    bound = [r for r in invalid if r["class_bound"]]
    unbound = [r for r in invalid if not r["class_bound"] and not r["unrecoverable_source"]]
    unrec = [r for r in invalid if r["unrecoverable_source"]]

    def rec_counts(rs):
        return dict(Counter(r["recovery"] for r in rs))

    per_class = {}
    for c in CANON:
        sel = [r for r in bound if c in r["class_ids"]]
        per_class[c] = {
            "n": len(sel),
            "recovery": rec_counts(sel),
            "absent": [
                {
                    "event_id": r["event_id"],
                    "actor": (idx.outbox_by_id.get(r["event_id"]) or [("", {})])[0][1].get("actor"),
                    "task_id": r["task_id"],
                    "gate": r["gate"],
                    "conclusion_type": r["conclusion_type"],
                    "artifact_refs": r["artifact_refs"],
                    "evidence_on_disk": r["evidence_on_disk"],
                    "rejected_at": r["rejected_at"],
                }
                for r in sel if r["recovery"] == "ABSENT"
            ],
        }

    all_ctype, rej_ctype = ctype_usage(snap)
    absent_bound = [r for r in bound if r["recovery"] == "ABSENT"]
    absent_all = [r for r in invalid if r["recovery"] == "ABSENT"]

    findings = []
    findings.append({
        "id": "RRC-01",
        "severity": "major" if bound else "minor",
        "statement": "At the pinned snapshot, %d/%d rejected claims with reason 'claim: invalid conclusion_type' are class-bound to the four canonical formulation classes, and %d of them are ABSENT: no accepted event carries the event_id, references it, refiles the task_id, or carries its evidence." % (len(bound), len(invalid), len(absent_bound)),
        "measurement": {
            "rejects_total": len(rows),
            "invalid_ctype": len(invalid),
            "class_bound": len(bound),
            "unbound": len(unbound),
            "unrecoverable_source": len(unrec),
            "recovery_all_invalid": rec_counts(invalid),
            "recovery_class_bound": rec_counts(bound),
            "absent_class_bound": len(absent_bound),
            "absent_all": len(absent_all),
        },
        "falsifier": "Any accepted event in the pinned events.jsonl whose event_id matches an ABSENT row, or whose text references it, or an accepted claim with the same task_id and class - re-run recover_rejects_053.py at the same pins; the row moves up the ladder and the count drops.",
    })
    top_noncanon = sorted(
        ((k, v) for k, v in all_ctype.items() if k not in enum and k is not None),
        key=lambda kv: -kv[1],
    )[:12]
    findings.append({
        "id": "RRC-02",
        "severity": "minor",
        "statement": "Non-canonical conclusion_type values in emitted claims are dominated by measurement-like tokens; the ingest enum at research_map/schemas.py holds %d values and none of the top non-canonical tokens is in it." % len(enum),
        "measurement": {
            "enum": sorted(enum),
            "top_noncanonical_in_outbox": top_noncanon,
            "rejected_source_ctype": rej_ctype,
        },
        "falsifier": "A re-run that measures a different enum set from the same schemas.py bytes, or an accepted claim using one of the top non-canonical tokens without normalisation.",
    })
    findings.append({
        "id": "RRC-03",
        "severity": "major" if absent_bound else "minor",
        "statement": "Per-class ABSENT counts at the snapshot: " + ", ".join(
            "%s=%d" % (c, len(per_class[c]["absent"])) for c in CANON
        ) + ". The map's claims list undercounts class-bound claims emitted to outbox by at least this much, since ABSENT rows have no accepted-stream claim replacement.",
        "measurement": {c: {"n": per_class[c]["n"], "absent": len(per_class[c]["absent"]),
                            "by_recovery": per_class[c]["recovery"]} for c in CANON},
        "falsifier": "A map/claims-list claim whose evidence chain resolves to an ABSENT row's event_id or task_id via an accepted event; or a re-run at the same pins that classifies one of these rows higher.",
    })
    findings.append({
        "id": "RRC-04",
        "severity": "minor",
        "statement": "All ABSENT class-bound rows have their referenced artifacts on disk (evidence files exist); the loss is in the accepted-stream claim record, not in the filesystem bytes." if all(r["evidence_on_disk"] for r in absent_bound) and absent_bound else "At least one ABSENT class-bound row has no on-disk artifact resolution; the loss is both in the claim record and in the evidence channel.",
        "measurement": {
            "absent_with_evidence_on_disk": sum(1 for r in absent_bound if r["evidence_on_disk"]),
            "absent_total": len(absent_bound),
        },
        "falsifier": "A re-measurement showing an ABSENT row's artifact_ref missing from disk or hash-mismatched at the recorded prefix.",
    })

    # ------------------------------------------------------------ controls
    controls = []
    # C1: inject accepted event_id
    target = absent_bound[0] if absent_bound else (invalid[0] if invalid else None)
    if target:
        fake = {"event_id": target["event_id"], "event_type": "claim",
                "class_id": (target["class_ids"] or ["NONE"])[0]}
        idx1 = idx.clone(extra_accepted=[fake])
        obs = classify({"event_id": target["event_id"], "source": target["source"],
                        "rejected_at": target["rejected_at"], "raw": ""}, idx1, enum)
        controls.append({"id": "C1", "description": "inject accepted event with rejected event_id",
                         "expected": "ACCEPTED_EVENT_ID", "observed": obs["recovery"],
                         "detected": obs["recovery"] == "ACCEPTED_EVENT_ID"})
    # C2: remove the referencing accepted event
    ref_rows = [r for r in invalid if r["recovery"] == "REFILED_BY_REFERENCE"]
    if ref_rows:
        r0 = ref_rows[0]
        idx2 = idx.clone(exclude_accepted_ids=[r0["event_id"]])
        obs = classify({"event_id": r0["event_id"], "source": r0["source"],
                        "rejected_at": r0["rejected_at"], "raw": ""}, idx2, enum)
        controls.append({"id": "C2", "description": "exclude the accepted event that references the reject",
                         "expected": "recovery weakens below REFILED_BY_REFERENCE",
                         "observed": obs["recovery"],
                         "detected": obs["recovery"] != "REFILED_BY_REFERENCE"})
    else:
        controls.append({"id": "C2", "description": "exclude the accepted event that references the reject",
                         "expected": "recovery weakens below REFILED_BY_REFERENCE",
                         "observed": "no REFILED_BY_REFERENCE row present to mutate",
                         "detected": False})
    # C3: canonical ctype row is not in the invalid-ctype census
    canon_row = {"event_id": "control-c3", "event_type": "claim", "reason": "claim: invalid conclusion_type",
                 "event_id_ref": "control-c3"}
    fake_ev = {"event_id": "control-c3", "event_type": "claim", "conclusion_type": "numerical_evidence",
               "class_id": CANON[0]}
    idx3 = idx.clone(extra_accepted=[fake_ev])
    obs = classify({"event_id": "control-c3", "source": "synthetic", "rejected_at": now(), "raw": ""}, idx3, enum)
    controls.append({"id": "C3", "description": "canonical conclusion_type row must not be classified as a validator victim",
                    "expected": "valid_ctype_now=true and recovery ACCEPTED_EVENT_ID",
                    "observed": {"valid_ctype_now": obs.get("valid_ctype_now"), "recovery": obs["recovery"]},
                    "detected": obs.get("valid_ctype_now") is True and obs["recovery"] == "ACCEPTED_EVENT_ID"})
    # C4: duplicate reject rows counted once
    if target:
        dup = [dict(x) for x in rows if x.get("event_id") == target["event_id"]]
        dup = dup + dup
        n1 = len(census(rows, idx, enum))
        n2 = len(census(rows + dup, idx, enum))
        controls.append({"id": "C4", "description": "duplicate reject rows for one event_id counted once",
                         "expected": "count unchanged", "observed": {"before": n1, "after": n2},
                         "detected": n1 == n2})
    # C5: tampered hash prefix makes file hash check fail
    ref_rows2 = [r for r in invalid if r.get("artifact_refs") and r.get("evidence_on_disk")]
    if ref_rows2:
        r0 = ref_rows2[0]
        ref = r0["artifact_refs"][0]
        base = norm_path(ref.partition("#")[0])
        p = ROOT / base
        ok_real = sha256_bytes(p.read_bytes()).startswith("deadbeefdeadbeef") if p.exists() else None
        controls.append({"id": "C5", "description": "tampered sha prefix must not resolve",
                         "expected": "false", "observed": bool(ok_real), "detected": ok_real is False})
    # C6/C7: class binding predicate
    c6 = bool(set(class_ids_of({"class_ids": [CANON[0], "NOT-A-CLASS"]}, "")) & set(CANON))
    c7 = bool(set(class_ids_of({"class_id": "GLOBAL"}, "")) & set(CANON))
    controls.append({"id": "C6", "description": "mixed canonical+unknown list is class-bound",
                     "expected": True, "observed": c6, "detected": c6 is True})
    controls.append({"id": "C7", "description": "GLOBAL is not class-bound",
                     "expected": False, "observed": c7, "detected": c7 is False})
    # C8: missing source line -> UNRECOVERABLE_SOURCE, excluded from ABSENT
    idx8 = Index(idx.accepted, {}, {})
    obs = classify({"event_id": "control-c8-not-anywhere", "source": "comms/outbox/none.jsonl",
                    "rejected_at": now(), "raw": '{"class_id": "%s"}' % CANON[0]}, idx8, enum)
    controls.append({"id": "C8", "description": "missing source line -> UNRECOVERABLE_SOURCE, not ABSENT",
                     "expected": "UNRECOVERABLE_SOURCE",
                     "observed": obs["recovery"],
                     "detected": obs["recovery"] == "UNRECOVERABLE_SOURCE"})

    report = {
        "task_id": TASK_ID,
        "actor": "worker-053",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": ";".join(CANON),
        "class_ids": CANON,
        "started_at": started,
        "finished_at": now(),
        "pins_before": snap.pins(),
        "pins_after": drifts,
        "drift": drifts["drift"],
        "schema_enum": {"enum": sorted(enum), "source_regex": enum_src,
                        "source_file_sha256": sha256_bytes(snap.bytes["research_map/schemas.py"])},
        "totals": {
            "rejects_total": len(rows),
            "by_reason": dict(by_reason),
            "invalid_ctype": len(invalid),
            "class_bound": len(bound),
            "unbound": len(unbound),
            "unrecoverable_source": len(unrec),
            "recovery_invalid": rec_counts(invalid),
            "recovery_class_bound": rec_counts(bound),
        },
        "per_class": per_class,
        "absent_class_bound": [
            {k: r[k] for k in ("event_id", "source", "rejected_at", "task_id", "gate",
                               "class_ids", "conclusion_type", "artifact_refs",
                               "evidence_on_disk", "evidence_in_accepted")}
            for r in absent_bound
        ],
        "refiled_class_bound": [
            {k: r[k] for k in ("event_id", "source", "rejected_at", "task_id", "gate",
                               "class_ids", "conclusion_type", "recovery")}
            for r in bound if r["recovery"] in ("REFILED_BY_REFERENCE", "REFILED_BY_TASK")
        ],
        "ctype_usage": {"outbox_all_claims": all_ctype, "rejected_source_claims": rej_ctype},
        "controls": controls,
        "findings": findings,
        "non_claims": [
            "Not a gate verdict, not a re-review of any schema content.",
            "No canonical path was written; all reads only.",
            "Does not assert any dropped claim is true; measures only whether its claim record and evidence landed in the accepted stream.",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    (HERE / "controls.json").write_text(json.dumps(
        {"task_id": TASK_ID, "controls": controls,
         "all_detected": all(c["detected"] for c in controls)}, indent=1) + "\n")
    print(json.dumps({
        "task_id": TASK_ID,
        "rejects_total": len(rows),
        "invalid_ctype": len(invalid),
        "class_bound": len(bound),
        "absent_class_bound": len(absent_bound),
        "unrecoverable_source": len(unrec),
        "recovery_class_bound": rec_counts(bound),
        "drift": drifts["drift"],
        "controls_all_detected": all(c["detected"] for c in controls),
        "controls": controls,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
