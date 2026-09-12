#!/usr/bin/env python3
"""FLASH-02 checkpoint daemon for the F0/G-F0 assignment window.

Every --interval seconds until --deadline it appends one checkpoint record:
  - artifact hashes for this worker's outputs (drift detection)
  - current taxonomy sha256 + revision (WARN if it moved since the previous checkpoint)
  - inbox line count/hash and whether a new message arrived after the assignment
  - outbox line count, map sha, elapsed minutes

Records: artifacts/flash-02/checkpoints/checkpoints.jsonl
Summary: artifacts/flash-02/checkpoints/CHECKPOINT.md
Exit: at the deadline, with a final record. Failures are recorded, not hidden.
"""
import argparse
import datetime
import hashlib
import json
import time
from pathlib import Path

CST = datetime.timezone(datetime.timedelta(hours=8))
WATCH = [
    "schemas/taxonomy_cases.jsonl",
    "artifacts/flash-02/leak_rule_catalog.json",
    "artifacts/flash-02/taxonomy_cases_check_report.json",
    "artifacts/flash-02/escape_matrix.json",
    "artifacts/flash-02/README.md",
]
TAX = Path("research_map/formulation_taxonomy.yaml")
MAP = Path("research_map/research_map.json")
INBOX = Path("comms/inbox/deepseek-flash-02.jsonl")
OUTBOX = Path("comms/outbox/deepseek-flash-02.jsonl")
CP = Path("artifacts/flash-02/checkpoints/checkpoints.jsonl")
MD = Path("artifacts/flash-02/checkpoints/CHECKPOINT.md")
ASSIGNMENT_ID = "asg-2026-09-11-F0-deepseek-flash-02-11"


def sha(p: Path) -> str:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except FileNotFoundError:
        return "MISSING"


def snap():
    return {
        "at": datetime.datetime.now(CST).isoformat(timespec="seconds"),
        "artifacts": {p: sha(Path(p))[:12] for p in WATCH},
        "taxonomy": {"sha256": sha(TAX)[:12],
                     "revision": _rev()},
        "map_sha": sha(MAP)[:12],
        "inbox_lines": _lines(INBOX),
        "inbox_sha": sha(INBOX)[:12],
        "outbox_lines": _lines(OUTBOX),
    }


def _rev():
    try:
        import yaml
        return yaml.safe_load(TAX.read_text()).get("revision")
    except Exception as e:
        return f"ERR:{e}"


def _lines(p: Path) -> int:
    try:
        return sum(1 for l in p.read_text().splitlines() if l.strip())
    except FileNotFoundError:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=900)
    ap.add_argument("--deadline", default="2026-09-12T03:15:00+08:00")
    a = ap.parse_args()
    deadline = datetime.datetime.fromisoformat(a.deadline)
    CP.parent.mkdir(parents=True, exist_ok=True)
    start = datetime.datetime.now(CST)
    prev = snap()
    i = 0
    while datetime.datetime.now(CST) < deadline:
        time.sleep(min(a.interval, max(5, (deadline - datetime.datetime.now(CST)).total_seconds())))
        i += 1
        cur = snap()
        drift = [k for k in cur["artifacts"] if cur["artifacts"][k] != prev["artifacts"].get(k)]
        tax_drift = cur["taxonomy"] != prev["taxonomy"]
        inbox_new = (cur["inbox_lines"] > prev["inbox_lines"]) or (cur["inbox_sha"] != prev["inbox_sha"])
        rec = {"ckpt_id": f"flash02-ckpt-{i:02d}", "elapsed_min": round((datetime.datetime.now(CST) - start).total_seconds() / 60, 1),
               **cur, "artifact_drift": drift, "taxonomy_moved": tax_drift, "inbox_changed": inbox_new,
               "note": "no action needed" if not (drift or tax_drift or inbox_new) else
                       "ACTION: re-run pin/checker if taxonomy moved; re-read inbox if changed; re-submit if own artifact drifted"}
        with open(CP, "a") as f:
            f.write(json.dumps(rec) + "\n")
        with open(MD, "a") as f:
            f.write(f"- {rec['ckpt_id']} {cur['at']} elapsed {rec['elapsed_min']}m "
                    f"tax_sha={cur['taxonomy']['sha256']} tax_moved={tax_drift} "
                    f"artifact_drift={drift} inbox_changed={inbox_new}\n")
        prev = cur
    print(f"checkpoint daemon finished at {datetime.datetime.now(CST).isoformat(timespec='seconds')}; "
          f"{i} checkpoints; last taxonomy {prev['taxonomy']}")


if __name__ == "__main__":
    main()
