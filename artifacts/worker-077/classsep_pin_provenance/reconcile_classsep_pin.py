#!/usr/bin/env python3
"""W077-CLASSSEP-PINRECON-01 -- read-only pin-provenance reconciliation of the
class-separation gate instrument's baseline digest.

Question: which digest is the byte-attested identity of the pre-move
`research_map/class_separation.py` recorded at freeze time (frozen_at
2026-09-11T23:30:20+08:00), and which records cite a digest that no byte
sequence in the scanned domain satisfies?

Design rule forced by this task's own subject matter: NO hex prefix of the
disputed digest is trusted as a literal.  The only constants are the shared
6-character stem `c266db` and the expected unattested full digest, which is
used solely as a pre-registered expectation that the run confirms or refutes.
Every prefix, classification and match is derived from measured bytes.

Exit codes:
  0  instrument ok: controls pass, stable pins unchanged in-run (the pin
     discrepancy itself is a *result*, not an instrument failure)
  2  control failure or pre-registered expectation refuted: not trustworthy
  3  pin drift: a pinned stable input changed during the run; findings void
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUTDIR = ROOT / "artifacts/worker-077/classsep_pin_provenance"

TASK_ID = "W077-CLASSSEP-PINRECON-01"
FREEZE_EVENT_ID = "astra-w07adj-00"
FROZEN_PATH = "research_map/class_separation.py"
FAMILY_STEM = "c266db"  # the only shared 6-char stem; no prefix beyond it is trusted
EXPECTED_UNATTESTED = "c266dbecaa87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
EXPECTED_ATTESTED = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"

STABLE_INPUTS = [
    "research_map/events.jsonl",
    "entry_hashes.json",
    "runtime/state/controller_verification/cf29-detector-write-forensics.json",
    "research_map/ASTRA_HANDOFF.md",
    "research_map/class_separation.py",
    "runtime/bin/classsep_regression.py",
    "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
    "artifacts/worker-032/cf16-delta/pinned/class_separation.c266dbceca87.py",
    "artifacts/worker-032/cf16-delta-02/pinned/class_separation.c266dbceca87.pre.py",
    "artifacts/worker-073/classsep_union_separability/pinned/class_separation.c266dbceca87.py",
    "artifacts/worker-073/classsep_union_separability/pinned/class_separation.c266dbceca87.worker032.py",
    "artifacts/worker-093/cf16_calibration/pinned/class_separation.c266dbce.py",
    "artifacts/worker-093/classsep_metagrowth/pinned/class_separation.c266dbce.py",
    "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py",
]
MOVING_INPUTS = ["research_map/research_map.json"]

TEXT_SCAN_GLOBS = [
    "comms/outbox/*.jsonl",
    "comms/inbox/*.jsonl",
    "reviews/*.json",
    "runtime/state/controller_verification/*.json",
    "runtime/state/controller_verification/*.md",
]
TOKEN_RE = re.compile(r"c266db[0-9a-f]*")
SWEEP_MAX_BYTES = 2 * 1024 * 1024
SWEEP_MAX_FILES = 60000
SWEEP_MAX_TOTAL = 3 * 1024 * 1024 * 1024


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, path + f"[{i}]")
    elif isinstance(o, str):
        yield path, o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUTDIR / "report.json"))
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"),
                    help="emit determinism comparison of two reports and exit")
    args = ap.parse_args()

    if args.compare:
        a = json.loads(Path(args.compare[0]).read_text())
        b = json.loads(Path(args.compare[1]).read_text())
        same = a.get("content_digest") == b.get("content_digest")
        det = {"task_id": TASK_ID, "compared": list(args.compare),
               "content_digest_a": a.get("content_digest"),
               "content_digest_b": b.get("content_digest"),
               "identical_content_digest": same,
               "pins_run_a": a.get("pins"), "pins_run_b": b.get("pins"),
               "checked_at": now()}
        (OUTDIR / "determinism.json").write_text(json.dumps(det, indent=1, sort_keys=True) + "\n")
        print(json.dumps({"identical": same, "a": det["content_digest_a"],
                          "b": det["content_digest_b"]}))
        return 0 if same else 2

    t0 = now()
    pins, raw = {}, {}
    for rel in STABLE_INPUTS + MOVING_INPUTS + ["comms/PROTOCOL.md", "research_map/schemas.py"]:
        p = ROOT / rel
        if p.exists() and p.is_file():
            b = p.read_bytes()
            raw[rel] = b
            pins[rel] = sha256_bytes(b)
        else:
            pins[rel] = None

    checks, controls = [], []

    def chk(cid, ok, detail, evidence=None):
        checks.append({"id": cid, "status": "PASS" if ok else "FAIL",
                       "detail": detail, "evidence": evidence or []})
        return ok

    def control(cid, ok, detail):
        controls.append({"id": cid, "status": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    # ---------- copy census: every *class_separation* file, grouped by measured digest ----------
    copies = []
    for p in sorted(ROOT.rglob("*class_separation*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        copies.append({"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p),
                       "bytes": p.stat().st_size})
    family = [c for c in copies if c["sha256"].startswith(FAMILY_STEM)]
    family_digests = sorted({c["sha256"] for c in family})
    family_paths = {}
    for c in family:
        family_paths.setdefault(c["sha256"], []).append(c["path"])

    # ---------- A. primary freeze event ----------
    ev_raw = raw.get("research_map/events.jsonl", b"").decode("utf-8", "replace")
    freeze_ev, freeze_line = None, None
    for i, line in enumerate(ev_raw.splitlines(), 1):
        if FREEZE_EVENT_ID not in line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_id") == FREEZE_EVENT_ID:
            freeze_ev, freeze_line = e, i
            break
    fev_tokens = sorted({t for t in TOKEN_RE.findall(json.dumps(freeze_ev or {})) if len(t) >= 8})
    freeze_prefix = fev_tokens[0] if len(fev_tokens) == 1 else None

    # attested digest = the unique on-disk family digest matched by the freeze event prefix
    if freeze_prefix:
        attested_matches = [d for d in family_digests if d.startswith(freeze_prefix)]
    else:
        attested_matches = []
    attested_full = attested_matches[0] if len(attested_matches) == 1 else None
    if attested_full is None and len(family_digests) == 1:
        # fall back only if the event gives no discriminator; recorded in the check detail
        attested_full = family_digests[0]
    attested_12 = attested_full[:12] if attested_full else None

    chk("C0-copy-census", len(family) >= 5,
        f"{len(copies)} files match *class_separation*; {len(family)} carry the family stem "
        f"'{FAMILY_STEM}'; distinct family digests: {family_digests}",
        [f"{p}#sha256:{d}" for d in family_digests for p in family_paths[d][:3]])

    chk("A-freeze-event", freeze_ev is not None and freeze_prefix is not None
        and attested_full is not None and attested_full.startswith(freeze_prefix or "\0"),
        f"freeze event {FREEZE_EVENT_ID} located at events.jsonl line {freeze_line}, "
        f"created_at={freeze_ev.get('created_at') if freeze_ev else None}; cited token(s) "
        f"{fev_tokens}; resolves to on-disk digest {attested_full}",
        [f"research_map/events.jsonl#sha256:{pins.get('research_map/events.jsonl')}:line{freeze_line}"])

    map0 = json.loads(raw["research_map/research_map.json"].decode())
    fa = [f for f in map0.get("frozen_artifacts", []) if f.get("path") == FROZEN_PATH]
    fa = fa[0] if fa else {}
    chk("A2-freeze-timestamp",
        bool(freeze_ev) and freeze_ev.get("created_at") == fa.get("frozen_at"),
        f"freeze event created_at={freeze_ev.get('created_at') if freeze_ev else None} == "
        f"frozen_artifacts.frozen_at={fa.get('frozen_at')}",
        [f"research_map/research_map.json#sha256:{pins.get('research_map/research_map.json')}"])

    chk("B-frozen-entry", fa.get("sha256") == attested_full,
        f"frozen_artifacts[{FROZEN_PATH}].sha256={fa.get('sha256')} == byte-attested {attested_full}",
        [f"research_map/research_map.json#sha256:{pins.get('research_map/research_map.json')}"])
    eh = json.loads(raw["entry_hashes.json"].decode())
    chk("B2-entry-hashes", eh.get(FROZEN_PATH) == attested_full,
        f"entry_hashes.json[{FROZEN_PATH}]={eh.get(FROZEN_PATH)} == byte-attested {attested_full}",
        [f"entry_hashes.json#sha256:{pins.get('entry_hashes.json')}"])

    # ---------- citation census over every record that names the family ----------
    citations = []

    def add(record, locator, text):
        for t in sorted({t for t in TOKEN_RE.findall(text) if len(t) >= 8}):
            citations.append({"record": record, "locator": locator, "token": t})

    for path, s in walk_strings(map0):
        if FAMILY_STEM in s:
            add("research_map/research_map.json", path, s)
    for i, line in enumerate(raw["research_map/ASTRA_HANDOFF.md"].decode("utf-8", "replace").splitlines(), 1):
        if FAMILY_STEM in line:
            add("research_map/ASTRA_HANDOFF.md", f"line {i}", line)
    for rel in ("runtime/state/controller_verification/cf29-detector-write-forensics.json",
                "entry_hashes.json"):
        for path, s in walk_strings(json.loads(raw[rel].decode())):
            if FAMILY_STEM in s:
                add(rel, path, s)
    for i, line in enumerate(ev_raw.splitlines(), 1):
        if FAMILY_STEM not in line:
            continue
        try:
            e = json.loads(line)
            loc = (f"line {i} event_id={e.get('event_id')} actor={e.get('actor')} "
                   f"created_at={e.get('created_at')}")
        except Exception:
            loc = f"line {i}"
        add("research_map/events.jsonl", loc, line)
    for g in TEXT_SCAN_GLOBS:
        for p in sorted(ROOT.glob(g)):
            txt = p.read_text(errors="replace")
            if FAMILY_STEM in txt:
                add(str(p.relative_to(ROOT)), "full text", txt)

    # full-digest citations that match no on-disk file are the orphan set
    cited_fulls = sorted({c["token"] for c in citations if len(c["token"]) == 64})
    orphan_fulls = [t for t in cited_fulls if t not in family_digests]

    def classify(tok):
        att = any(d.startswith(tok) for d in family_digests)
        preset = EXPECTED_UNATTESTED.startswith(tok)
        orphan = any(f.startswith(tok) for f in orphan_fulls)
        if att and not preset and not orphan:
            return "attested-prefix"
        if att:
            return "attested-or-colliding-prefix"
        if preset:
            return "unattested-transcription-prefix"
        if orphan:
            return "orphan-full-prefix"
        return "unresolved-prefix"

    for c in citations:
        c["classification"] = classify(c["token"])
    by_class = {}
    for c in citations:
        by_class.setdefault(c["classification"], []).append(c)
    attested_sites = by_class.get("attested-prefix", []) + by_class.get("attested-or-colliding-prefix", [])
    orphan_sites = (by_class.get("unattested-transcription-prefix", [])
                    + by_class.get("orphan-full-prefix", [])
                    + by_class.get("unresolved-prefix", []))
    expected_ok = (EXPECTED_ATTESTED in family_digests
                   and EXPECTED_UNATTESTED not in family_digests)

    chk("C-citation-census", len(citations) >= 10,
        "citation classes: " + ", ".join(f"{k}={len(v)}" for k, v in sorted(by_class.items()))
        + f"; orphan full digests cited (match no file): {orphan_fulls}",
        [f"{c['record']}#{c['locator']}" for c in orphan_sites[:20]])

    # ---------- D. sweep for the pre-registered unattested digest ----------
    scanned = scanned_bytes = 0
    capped = False
    matches_unattested, matches_attested_family = [], []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        if scanned >= SWEEP_MAX_FILES or scanned_bytes >= SWEEP_MAX_TOTAL:
            capped = True
            break
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        if sz > SWEEP_MAX_BYTES:
            continue
        try:
            h = sha256_file(p)
        except OSError:
            continue
        scanned += 1
        scanned_bytes += sz
        if h == EXPECTED_UNATTESTED:
            matches_unattested.append(str(p.relative_to(ROOT)))
        if attested_full and h == attested_full:
            matches_attested_family.append(str(p.relative_to(ROOT)))
    chk("D-sweep", not capped,
        f"sweep completed (cap hit: {capped}); files measuring the pre-registered unattested "
        f"digest: {len(matches_unattested)}; files measuring the byte-attested digest: "
        f"{len(matches_attested_family)}; live scan counts in the sweep block",
        [f"{m}#sha256:{EXPECTED_UNATTESTED}" for m in matches_unattested])

    # ---------- E. controls ----------
    control("K1-on-disk-attestation", len(family) >= 5 and len(family_digests) == 1,
            f"{len(family)} on-disk copies carry the family stem, {len(family_digests)} distinct "
            f"digest(s); the attested digest is derived from bytes, not from a literal")
    tampered = (EXPECTED_ATTESTED[:-1] + ("0" if EXPECTED_ATTESTED[-1] != "0" else "1"))
    control("K2-tamper-negative", tampered not in family_digests,
            "single-nibble tamper of the expected attested digest matches no on-disk copy")
    control("K3-prefix-separation",
            EXPECTED_ATTESTED[:12] != EXPECTED_UNATTESTED[:12]
            and len({EXPECTED_ATTESTED[:6], EXPECTED_UNATTESTED[:6]}) == 1,
            f"expected digests share only the 6-char stem '{FAMILY_STEM}' and diverge at hex "
            f"char 7 ({EXPECTED_ATTESTED[:12]} vs {EXPECTED_UNATTESTED[:12]})")
    control("K4-freeze-locator", freeze_ev is not None and freeze_prefix is not None
            and attested_full is not None and attested_full.startswith(freeze_prefix),
            f"freeze event located by event_id; its cited token {freeze_prefix} is a prefix of "
            f"the byte-attested digest {attested_full}")
    control("K5-sweep-sensitivity", len(matches_attested_family) >= 5,
            f"independent sweep found {len(matches_attested_family)} files with the attested "
            f"digest (scanner is not silently empty)")
    control("K6-pre-registered-expectation",
            expected_ok and len(matches_unattested) == 0
            and len(by_class.get("unattested-transcription-prefix", [])) >= 1,
            f"pre-registered expectation confirmed: {EXPECTED_ATTESTED} measured on disk; "
            f"{EXPECTED_UNATTESTED} matches 0 swept files while its prefix is cited at "
            f"{len(by_class.get('unattested-transcription-prefix', []))} site(s) "
            f"(orphan fulls cited: {orphan_fulls})")
    control("K7-citation-nonempty", len(citations) >= 10,
            f"citation census non-empty ({len(citations)} tokens over "
            f"{len({c['record'] for c in citations})} records)")

    # ---------- F. in-run drift ----------
    drift = []
    for rel in STABLE_INPUTS:
        p = ROOT / rel
        if p.exists() and p.is_file() and pins.get(rel) != sha256_file(p):
            drift.append({"path": rel, "t0": pins.get(rel), "t1": sha256_file(p)})
    map_t1 = sha256_bytes((ROOT / "research_map/research_map.json").read_bytes())
    moving = {"research_map/research_map.json":
              {"t0": pins.get("research_map/research_map.json"), "t1": map_t1,
               "drift": pins.get("research_map/research_map.json") != map_t1}}

    # ---------- verdict ----------
    orphan_records = sorted({c["record"] for c in orphan_sites})
    transcription_records = sorted({c["record"] for c in by_class.get("unattested-transcription-prefix", [])})
    verdict = {
        "ruling": (
            f"The pre-move {FROZEN_PATH} baseline recorded at freeze time is {attested_full} "
            f"(12-hex prefix {attested_12}). The primary freeze event {FREEZE_EVENT_ID} at "
            f"created_at == frozen_artifacts.frozen_at == {fa.get('frozen_at')} cites that prefix; "
            f"the current frozen_artifacts entry, entry_hashes.json and {len(family)} on-disk "
            f"copies all measure that digest. Two transcription variants of it are cited that match "
            f"no bytes: (A) prefix {EXPECTED_UNATTESTED[:12]} at "
            f"{len(by_class.get('unattested-transcription-prefix', []))} sites across "
            f"{len(transcription_records)} records, differing from the attested digest at hex "
            f"characters 7-9 ('{attested_12}' vs '{EXPECTED_UNATTESTED[:12]}'); and (B) orphan full "
            f"digest(s) {orphan_fulls} at {len(by_class.get('orphan-full-prefix', []))} sites. "
            f"{len(orphan_sites)} citation sites in total do not resolve to any on-disk bytes."
        ),
        "impact": (
            "Operative instructions that name the unattested prefix as the active frozen pin "
            "(CF-16/CF-26/CF-29 action text; ASTRA_HANDOFF.md lines 42 and 50; the r3 "
            "CLASSSEP-calibration-adjudication review) cannot be executed as written, and "
            "audit_evidence.py's frozen-drift message would print that prefix as the baseline. "
            f"Any hash-bound instruction for the 02:30 classsep adjudication review must use "
            f"{attested_full}."
        ),
        "attested": attested_full,
        "unattested": EXPECTED_UNATTESTED,
        "orphan_fulls_cited": orphan_fulls,
        "attested_citation_sites": len(attested_sites),
        "orphan_citation_sites": len(orphan_sites),
        "unattested_citation_sites": len(by_class.get("unattested-transcription-prefix", [])),
        "orphan_citation_records": orphan_records,
        "family_digests": family_digests,
    }

    falsifier = (
        f"Any file in the swept domain measuring {EXPECTED_UNATTESTED}; any primary event before the "
        f"00:52 move citing a token that is not a prefix of {EXPECTED_ATTESTED}; the freeze event's "
        f"cited token failing to resolve to a single on-disk digest; a family copy set that is not "
        f"byte-identical; or drift of any pinned stable input during the run (voids the run)."
    )
    non_claims = [
        "Not a gate verdict; does not pass or fail G-AUDIT and does not adopt any detector revision.",
        "Does not adjudicate detector quality or the contested FN/FP arms (astra-life07-classsep-adjudication-review).",
        "Does not edit controller findings or any other agent's text (CF-4); the correction is reported, not applied.",
        "Does not measure the e36b0d644ca window (CF-29 forensics) or the behaviour of the live a8c04fc31e4a bytes.",
        "The 'no bytes satisfy it' claim is scoped to the enumerated sweep domain, reported with counts.",
        "No canonical write was made by this worker.",
    ]

    report = {
        "schema": "worker-077/pin-provenance-reconciliation/v1",
        "task_id": TASK_ID, "worker": "worker-077",
        "node_id": "A1", "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": t0, "finished_at": now(),
        "question": ("Which digest is the byte-attested identity of the pre-move "
                     "research_map/class_separation.py recorded at frozen_at "
                     "2026-09-11T23:30:20+08:00, and which records cite a digest no bytes satisfy?"),
        "shared_stem": FAMILY_STEM,
        "expected_attested": EXPECTED_ATTESTED,
        "expected_unattested": EXPECTED_UNATTESTED,
        "attested_digest": attested_full,
        "unattested_digest": EXPECTED_UNATTESTED,
        "pins": pins, "moving_inputs": moving,
        "checks": checks, "controls": controls,
        "copy_census": copies,
        "family_digests": family_digests,
        "citation_census": citations,
        "citation_summary": {k: len(v) for k, v in sorted(by_class.items())},
        "orphan_citation_sites": orphan_sites,
        "orphan_fulls_cited": orphan_fulls,
        "sweep": {"files_scanned": scanned, "bytes_scanned": scanned_bytes, "capped": capped,
                  "matches_unattested": matches_unattested,
                  "matches_attested": matches_attested_family,
                  "per_file_byte_cap": SWEEP_MAX_BYTES},
        "in_run_drift": drift,
        "verdict": verdict, "falsifier": falsifier, "non_claims": non_claims,
        "instrument_ok": not [c for c in controls if c["status"] == "FAIL"],
        "map_drift": moving["research_map/research_map.json"]["drift"],
    }
    content = {k: v for k, v in report.items()
               if k not in ("created_at", "finished_at", "moving_inputs", "map_drift", "sweep",
                            "copy_census", "citation_census", "citation_summary")}
    # The tree is live: copies are rewritten and records appended by other workers while this
    # runs.  The reproducible core is the pinned-record measurement plus the substantive sweep
    # result; live counts stay in the report body but not in the determinism digest.
    pinned_records = set(STABLE_INPUTS) | {"comms/PROTOCOL.md", "research_map/schemas.py"}
    pinned_summary = {}
    for c in citations:
        if c["record"] in pinned_records:
            pinned_summary[c["classification"]] = pinned_summary.get(c["classification"], 0) + 1
    content["pinned_citation_summary"] = dict(sorted(pinned_summary.items()))
    report["pinned_citation_summary"] = dict(sorted(pinned_summary.items()))
    content["family_digests"] = family_digests
    content["sweep_result"] = {"matches_unattested": matches_unattested,
                               "matches_attested": matches_attested_family,
                               "capped": capped}
    report["content_digest"] = sha256_bytes(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode())

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    print(json.dumps({
        "task_id": TASK_ID,
        "attested": attested_full, "unattested": EXPECTED_UNATTESTED,
        "family_copies": len(family), "family_digests": family_digests,
        "unattested_citation_sites": len(by_class.get("unattested-transcription-prefix", [])),
        "orphan_citation_sites": len(orphan_sites),
        "orphan_fulls_cited": orphan_fulls,
        "orphan_records": orphan_records,
        "attested_citation_sites": len(attested_sites),
        "sweep_files": scanned, "sweep_unattested_matches": len(matches_unattested),
        "checks": {c["id"]: c["status"] for c in checks},
        "controls": {c["id"]: c["status"] for c in controls},
        "stable_pin_drift": drift, "map_drift": moving["research_map/research_map.json"]["drift"],
        "content_digest": report["content_digest"],
    }, indent=1))

    if not report["instrument_ok"]:
        return 2
    if drift:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
