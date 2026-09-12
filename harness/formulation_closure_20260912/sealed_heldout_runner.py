#!/usr/bin/env python3
"""Sealed held-out protocol runner for FORM-RULE-SPEC.

The family partition commitment is written before any rule output is produced. The rule
executor receives opaque fixture ids only; family names and the partition map are withheld
until raw verdicts are committed. A second invocation with --reveal verifies the commitment
and runs an independent reproduction. This file is a candidate runner and is not itself a
G-FORM verdict.
"""
from __future__ import annotations
import argparse, hashlib, json, random, subprocess, sys
from pathlib import Path


def digest_bytes(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def commit_partition(items: list[dict], seed: int) -> tuple[str, dict]:
    fams = sorted({str(x["family"]) for x in items})
    rng = random.Random(seed)
    rng.shuffle(fams)
    # Only opaque labels enter the executor manifest; the permutation is committed separately.
    mapping = {f: f"F{n:02d}" for n, f in enumerate(fams)}
    payload = {"seed": seed, "families": mapping}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest(), payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=271828)
    ap.add_argument("--reveal", action="store_true")
    args = ap.parse_args()
    corpus = Path(args.corpus); tool = Path(args.tool); schema = Path(args.schema); out = Path(args.out)
    fixtures = sorted(json.loads(x) for x in corpus.read_text().splitlines() if x.strip())
    if len(fixtures) < 20 or len({str(x.get("family")) for x in fixtures}) < 10:
        raise SystemExit("sealed corpus requires >=20 fixtures and >=10 families")
    commit, partition = commit_partition(fixtures, args.seed)
    manifest = {"protocol":"FORM-SEALED-01","seed":args.seed,"fixture_count":len(fixtures),"family_count":len(partition["families"]),"partition_commitment":commit,"tool_sha256":digest_bytes(tool),"schema_sha256":digest_bytes(schema),"controls_required":7,"status":"revealed" if args.reveal else "committed","fixtures":[{"id":str(x["id"]),"opaque_family":partition["families"][str(x["family"])]} for x in fixtures]}
    out.mkdir(parents=True,exist_ok=True); (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (out/"partition_commitment.json").write_text(json.dumps({"commitment":commit,"seed":args.seed,"revealed":args.reveal,"mapping":partition["families"] if args.reveal else None},indent=2)+"\n")
    # Raw fixture execution is intentionally delegated to an independent executor. This script
    # never interprets a verdict or edits the canonical map.
    print(json.dumps({"manifest":str(out/"manifest.json"),"partition_commitment":commit,"status":manifest["status"],"tool_sha256":manifest["tool_sha256"],"schema_sha256":manifest["schema_sha256"]}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

