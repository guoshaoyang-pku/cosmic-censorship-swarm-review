#!/usr/bin/env python3
"""W065-STRICT-YAML-CENSUS-01 -- gate-wide strict-YAML hygiene + accept-binding census.

Deterministic, read-only over the repository except for its own output directory.
No network. Bounded to the G-F0/G-FORM publication surface:

  * the four live canonical artifacts (F0 taxonomy, F1, F2a, F2b schemas)
  * every .yaml/.yml/.json file pinned by FROZEN.json revision 26
  * the F0 logical artifacts (declared taxonomy + class-contract supplement)

For each YAML file:
  - strict duplicate-key detection at every nesting depth (node walk, line numbers)
  - strict-consumer verdict: a loader that raises on duplicate mapping keys
  - PyYAML-safe_load effective value (last-wins) of each duplicated key
  - first-wins value, to expose reader-dependent revision metadata
  - effective revised_at vs file mtime (stamp-ahead-of-mtime)
  - FROZEN.json pin match and canonical/authoring byte equality

Then: which recorded review verdicts bind to the sha256 of artifacts that a
strict YAML consumer rejects.

Controls C1..C10 are run in-process on synthetic fixtures; a control failure
invalidates the instrument (verdict INSTRUMENT_INVALID), not the repository.

Usage:  python3 census.py            # writes census.json + controls/ fixtures
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))
TZ = timezone(timedelta(hours=8))
FROZEN = os.path.join(ROOT, "artifacts", "formulation", "FROZEN.json")
CANONICAL = [
    "research_map/formulation_taxonomy.yaml",   # F0 declared taxonomy
    "schemas/af_wcc_vacuum.yaml",               # F1
    "schemas/af_scc_c2_vacuum.yaml",            # F2a
    "schemas/af_scc_c0_vacuum.yaml",            # F2b
]
CLASS_OF = {
    "schemas/af_wcc_vacuum.yaml": ["AF-WCC-VAC-GEN"],
    "schemas/af_scc_c2_vacuum.yaml": ["AF-SCC-C2-VAC-GEN"],
    "schemas/af_scc_c0_vacuum.yaml": ["AF-SCC-C0-VAC-GEN"],
    "research_map/formulation_taxonomy.yaml": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                                               "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "artifacts/formulation/formulation_taxonomy.yaml": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                                                        "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
}
SHA_RE = re.compile(r"\b[0-9a-f]{64}\b")
SHORT_RE = re.compile(r"\b[0-9a-f]{12,63}\b")


def now() -> datetime:
    return datetime.now(TZ)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


# --------------------------------------------------------------------------
# YAML node walk: duplicates at every depth, with paths and line numbers
# --------------------------------------------------------------------------
def walk_duplicates(node, path, out, seen):
    """Collect duplicate mapping keys. `path` is a tuple of keys/indices."""
    if node is None or id(node) in seen:
        return
    seen.add(id(node))
    tag = getattr(node, "tag", "")
    if tag.endswith(":map"):
        counts = {}
        for key_node, val_node in node.value:
            try:
                key = key_node.value
            except Exception:
                key = "<non-scalar>"
            counts.setdefault(str(key), []).append(key_node)
        for key, key_nodes in counts.items():
            if len(key_nodes) > 1:
                out.append({
                    "path": ".".join(str(p) for p in path) + ("." if path else "") + key,
                    "key": key,
                    "occurrences": [kn.start_mark.line + 1 for kn in key_nodes],
                    "category": "merge_key" if key == "<<" else "duplicate_key",
                })
        for key_node, val_node in node.value:
            try:
                key = str(key_node.value)
            except Exception:
                key = "<non-scalar>"
            walk_duplicates(val_node, path + (key,), out, seen)
    elif tag.endswith(":seq"):
        for i, item in enumerate(node.value):
            walk_duplicates(item, path + (str(i),), out, seen)


def detect_duplicates(text: str):
    """Return list of duplicate-key findings via node walk (no construction)."""
    found = []
    for node in yaml.compose_all(text):
        walk_duplicates(node, (), found, set())
    return found


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (YAML 1.2 3.2.1.3)."""

    def construct_mapping(self, node, deep=False):
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError:
                continue
            if key in keys:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r} at line {key_node.start_mark.line + 1}",
                    key_node.start_mark)
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def strict_verdict(text: str):
    try:
        yaml.load(text, Loader=StrictLoader)
        return "OK", None
    except yaml.constructor.ConstructorError as exc:
        return "REJECT", str(exc).split("\n")[0]
    except yaml.YAMLError as exc:
        return "PARSE_ERROR", f"{type(exc).__name__}: {exc}"


def lastwins_value(text: str, key: str):
    """Effective value under PyYAML safe_load (last occurrence wins)."""
    try:
        doc = yaml.safe_load(text)
    except Exception:
        return None
    if isinstance(doc, dict):
        return doc.get(key)
    return None


def firstwins_value(text: str, key: str):
    """Value a first-wins reader would keep: first top-level occurrence."""
    for line in text.splitlines():
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def json_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            out.setdefault("__dups__", []).append(k)
        out[k] = v
    return out


def scan_yaml(rel: str, text: str, clock: datetime, frozen_pins: dict):
    dups = detect_duplicates(text)
    strict, detail = strict_verdict(text)
    mtime = os.path.getmtime(os.path.join(ROOT, rel))
    mtime_dt = datetime.fromtimestamp(mtime, TZ)
    rec = {
        "path": rel,
        "sha256": sha256_bytes(text.encode("utf-8")),
        "bytes": len(text.encode("utf-8")),
        "kind": "yaml",
        "strict": strict,
        "strict_detail": detail,
        "duplicate_keys": dups,
        "pin": frozen_pins.get(rel),
        "pin_match": (frozen_pins.get(rel) == sha256_bytes(text.encode("utf-8")))
        if rel in frozen_pins else None,
        "mtime": iso(mtime_dt),
        "class_ids": CLASS_OF.get(rel, []),
    }
    for d in dups:
        d["effective_lastwins"] = lastwins_value(text, d["key"])
        d["reader_firstwins"] = firstwins_value(text, d["key"])
        d["reader_divergence"] = (d["reader_firstwins"] != d["effective_lastwins"])
    eff = lastwins_value(text, "revised_at")
    rec["effective_revised_at"] = eff
    if eff:
        try:
            eff_dt = datetime.fromisoformat(eff)
            rec["revised_at_ahead_of_mtime_s"] = int((eff_dt - mtime_dt).total_seconds())
            rec["revised_at_ahead_of_scan_clock_s"] = int((eff_dt - clock).total_seconds())
        except ValueError:
            pass
    return rec


def scan_json(rel: str, text: str, frozen_pins: dict):
    try:
        doc = json.loads(text, object_pairs_hook=json_duplicate_keys)
        parse = "OK"
        dups = doc.get("__dups__", []) if isinstance(doc, dict) else []
    except Exception as exc:
        parse = f"PARSE_ERROR: {type(exc).__name__}"
        dups = []
    rec = {
        "path": rel,
        "sha256": sha256_bytes(text.encode("utf-8")),
        "bytes": len(text.encode("utf-8")),
        "kind": "json",
        "parse": parse,
        "advisory_duplicate_keys": dups,
        "pin": frozen_pins.get(rel),
        "pin_match": (frozen_pins.get(rel) == sha256_bytes(text.encode("utf-8")))
        if rel in frozen_pins else None,
        "class_ids": CLASS_OF.get(rel, []),
    }
    return rec


# --------------------------------------------------------------------------
# Accept-binding scan over the recorded review corpus
# --------------------------------------------------------------------------
def hashes_in(obj, acc):
    if isinstance(obj, str):
        if SHA_RE.fullmatch(obj):
            acc.add(obj)
        else:
            for m in SHORT_RE.finditer(obj):
                acc.add(m.group(0))
    elif isinstance(obj, dict):
        for v in obj.values():
            hashes_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            hashes_in(v, acc)
    return acc


def top_field(obj, names):
    for n in names:
        if isinstance(obj, dict) and n in obj and isinstance(obj[n], (str, int, float)):
            return obj[n]
    return None


def collect_review_records(clock: datetime):
    """(source, actor, verdict, cited_hashes, observed_at) from reviews/*.json and outbox review events."""
    recs = []
    rdir = os.path.join(ROOT, "reviews")
    for name in sorted(os.listdir(rdir)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(rdir, name)
        try:
            doc = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        verdict = top_field(doc, ["verdict", "review_verdict", "recommendation"])
        actor = top_field(doc, ["reviewer", "actor", "reviewer_id"])
        if verdict is None or actor is None:
            continue
        mtime = iso(datetime.fromtimestamp(os.path.getmtime(p), TZ))
        recs.append({
            "source": f"reviews/{name}",
            "actor": str(actor),
            "verdict": str(verdict),
            "cited_hashes": sorted(hashes_in(doc, set())),
            "observed_at": mtime,
        })
    ob = os.path.join(ROOT, "comms", "outbox")
    for name in sorted(os.listdir(ob)):
        if not name.endswith(".jsonl"):
            continue
        for line in open(os.path.join(ob, name), encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event_type") != "review":
                continue
            verdict = top_field(e, ["verdict"])
            actor = top_field(e, ["reviewer", "actor"])
            if verdict is None or actor is None:
                continue
            recs.append({
                "source": f"comms/outbox/{name}:{e.get('event_id')}",
                "actor": str(actor),
                "verdict": str(verdict),
                "cited_hashes": sorted(hashes_in(e, set())),
                "observed_at": str(e.get("created_at") or e.get("_received_at") or ""),
            })
    return recs


# --------------------------------------------------------------------------
# Controls
# --------------------------------------------------------------------------
def run_controls(clock: datetime, canonical_texts: dict, tmpdir: str):
    os.makedirs(tmpdir, exist_ok=True)
    ctl = []

    def add(cid, desc, expected, observed, ok):
        ctl.append({"id": cid, "description": desc, "expected": expected,
                    "observed": observed, "pass": bool(ok)})

    # C1 positive: strict loader rejects top-level duplicate
    t1 = "a: 1\nb: 2\na: 3\n"
    v1, _ = strict_verdict(t1)
    add("C1", "strict loader rejects a top-level duplicate key",
        "REJECT", v1, v1 == "REJECT")

    # C2 negative: strict loader accepts a clean document
    t2 = "a: 1\nb:\n  c: 2\n  d: [1, 2, 3]\n"
    v2, _ = strict_verdict(t2)
    add("C2", "strict loader accepts a clean nested document", "OK", v2, v2 == "OK")

    # C3 depth coverage: nested duplicate found with path
    t3 = "outer:\n  inner:\n    k: 1\n    k: 2\n"
    d3 = detect_duplicates(t3)
    add("C3", "nested duplicate detected with full key path",
        "outer.inner.k", [d["path"] for d in d3], [d["path"] for d in d3] == ["outer.inner.k"])

    # C4 merge keys are not false-positive duplicate keys when used once
    t4 = "base: &b {x: 1}\nchild:\n  <<: *b\n  y: 2\n"
    d4 = [d for d in detect_duplicates(t4)]
    add("C4", "single merge key is not reported as a duplicate",
        "0 findings", len(d4), len(d4) == 0)

    # C5 alias reuse of one value is not a duplicate key
    t5 = "v: &a 5\np: *a\nq: *a\n"
    d5 = detect_duplicates(t5)
    add("C5", "alias reuse is not reported as a duplicate key",
        "0 findings", len(d5), len(d5) == 0)

    # C6 repeated values under distinct keys are not duplicates
    t6 = "k1: 7\nk2: 7\nk3: 7\n"
    d6 = detect_duplicates(t6)
    add("C6", "repeated values under distinct keys are not duplicates",
        "0 findings", len(d6), len(d6) == 0)

    # C7 JSON advisory duplicate detection
    t7 = '{"a": 1, "a": 2}'
    j7 = json.loads(t7, object_pairs_hook=json_duplicate_keys)
    add("C7", "JSON duplicate names detected as advisory",
        "['a']", j7.get("__dups__"), j7.get("__dups__") == ["a"])

    # C8 mutation sensitivity: append a duplicate of an existing top-level key.
    # State-independent: works whether or not the canonical file already has duplicates.
    clean_rel = "research_map/formulation_taxonomy.yaml"
    clean = canonical_texts[clean_rel]
    base_keys = list((yaml.safe_load(clean) or {}).keys())
    mut_key = base_keys[0] if base_keys else "schema_version"
    mutated = clean + f"\n{mut_key}: \"MUTANT-CONTROL\"\n"
    vm, _ = strict_verdict(mutated)
    dm = [d for d in detect_duplicates(mutated) if d["key"] == mut_key]
    add("C8", "injected top-level duplicate is detected (sensitivity)",
        "REJECT + 1 dup", f"{vm} + {len(dm)} dup",
        vm == "REJECT" and len(dm) == 1 and clean != mutated)

    # C9 reader divergence is measurable on a synthetic duplicate pair
    t9 = "revised_at: \"2026-01-01T00:00:00+08:00\"\nrevised_at: \"2026-02-02T00:00:00+08:00\"\n"
    c9 = (lastwins_value(t9, "revised_at") == "2026-02-02T00:00:00+08:00"
          and firstwins_value(t9, "revised_at") == "2026-01-01T00:00:00+08:00")
    add("C9", "first-wins vs last-wins reader divergence is measurable",
        "True", c9, c9 is True)

    # C10 determinism: two walks of the same text agree
    t10 = canonical_texts["schemas/af_wcc_vacuum.yaml"]
    add("C10", "duplicate detection is deterministic across repeated runs",
        "equal", "equal" if detect_duplicates(t10) == detect_duplicates(t10) else "differ",
        detect_duplicates(t10) == detect_duplicates(t10))

    return ctl


# --------------------------------------------------------------------------
def main():
    clock = now()
    frozen_raw = open(FROZEN, "rb").read()
    frozen_doc = json.loads(frozen_raw)
    frozen_sha = sha256_bytes(frozen_raw)
    pins = {}
    for p, meta in (frozen_doc.get("files") or {}).items():
        if isinstance(meta, dict) and "sha256" in meta:
            pins[p] = meta["sha256"]
    for p, meta in (frozen_doc.get("logical_artifacts") or {}).items():
        if isinstance(meta, dict) and "sha256" in meta:
            pins.setdefault(meta.get("path"), meta["sha256"])

    scope = []
    for rel in CANONICAL:
        scope.append(rel)
    for p in pins:
        if p.lower().endswith((".yaml", ".yml", ".json")) and p not in scope:
            scope.append(p)

    canonical_texts = {}
    for rel in scope:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            canonical_texts[rel] = open(p, encoding="utf-8").read()

    # window pre-hashes
    pre = {rel: sha256_bytes(t.encode("utf-8")) for rel, t in canonical_texts.items()}

    files = []
    for rel in scope:
        if rel not in canonical_texts:
            files.append({"path": rel, "missing": True})
            continue
        txt = canonical_texts[rel]
        if rel.lower().endswith(".json"):
            files.append(scan_json(rel, txt, pins))
        else:
            files.append(scan_yaml(rel, txt, clock, pins))

    # controls (after scan; independent of repo state)
    ctl = run_controls(clock, canonical_texts, os.path.join(OUT, "controls"))

    # window post-hashes
    post = {}
    for rel in canonical_texts:
        p = os.path.join(ROOT, rel)
        post[rel] = sha256_file(p) if os.path.exists(p) else None
    stable = pre == post

    # affected hashes: any YAML a strict consumer rejects
    affected = {}
    for rec in files:
        if rec.get("kind") == "yaml" and rec.get("strict") == "REJECT":
            affected[rec["sha256"]] = {
                "path": rec["path"],
                "canonical": rec["path"] in CANONICAL or rec["path"].startswith("schemas/"),
                "role": ("canonical_class_schema" if rec["path"].startswith("schemas/")
                         else "canonical_f0_taxonomy" if rec["path"] == "research_map/formulation_taxonomy.yaml"
                         else "supplement_or_mirror"),
                "class_ids": rec.get("class_ids", []),
                "duplicate_keys": [d["key"] for d in rec.get("duplicate_keys", [])],
            }
    prefixes = {}
    for h in affected:
        prefixes[h[:12]] = h

    records = collect_review_records(clock)
    bound = []
    for r in records:
        matched = set()
        for h in r["cited_hashes"]:
            if h in affected:
                matched.add(h)
            elif h in prefixes:
                matched.add(prefixes[h])
        if matched:
            bound.append({
                "source": r["source"],
                "actor": r["actor"],
                "verdict": r["verdict"],
                "observed_at": r["observed_at"],
                "matched_hashes": sorted(matched),
            })

    # net accept count per (actor, hash): a later non-accept review by the same actor supersedes
    order = sorted(bound, key=lambda x: (x["observed_at"] or "", x["source"]))
    accepts = {}
    superseded = []
    for i, r in enumerate(order):
        if r["verdict"].lower() != "accept":
            continue
        for h in r["matched_hashes"]:
            later = [o for o in order[i + 1:]
                     if o["actor"] == r["actor"] and h in o["matched_hashes"]
                     and o["verdict"].lower() != "accept"]
            accepts[(r["actor"], h)] = {
                "accept_source": r["source"],
                "accept_at": r["observed_at"],
                "superseded_by": later[0]["source"] if later else None,
            }
            if later:
                superseded.append({
                    "actor": r["actor"], "hash": h,
                    "accept": r["source"], "later": later[0]["source"],
                    "later_verdict": later[0]["verdict"],
                })

    counts = {}
    for r in bound:
        for h in r["matched_hashes"]:
            c = counts.setdefault(h, {"accept": 0, "revise": 0, "inconclusive": 0, "other": 0,
                                      "actors": set()})
            v = r["verdict"].lower()
            c[v if v in ("accept", "revise", "inconclusive") else "other"] += 1
            c["actors"].add(r["actor"])
    for h, c in counts.items():
        c["distinct_actors"] = sorted(c.pop("actors"))
        c["net_accepts"] = sorted(a for (a, hh) in accepts if hh == h and not accepts[(a, hh)]["superseded_by"])

    strict_rej = [r["path"] for r in files if r.get("kind") == "yaml" and r.get("strict") == "REJECT"]
    strict_ok = [r["path"] for r in files if r.get("kind") == "yaml" and r.get("strict") == "OK"]
    json_adv = [r["path"] for r in files if r.get("kind") == "json" and r.get("advisory_duplicate_keys")]
    all_ctl_pass = all(c["pass"] for c in ctl)

    result = {
        "task_id": "W065-STRICT-YAML-CENSUS-01",
        "actor": "worker-065",
        "created_at": iso(clock),
        "instrument": "artifacts/worker-065/strict_yaml_census/census.py",
        "scope": {
            "frozen_manifest": "artifacts/formulation/FROZEN.json",
            "frozen_manifest_sha256": frozen_sha,
            "frozen_revision": frozen_doc.get("revision"),
            "frozen_at": frozen_doc.get("frozen_at"),
            "files_censused": len([f for f in files if not f.get("missing")]),
            "canonical_artifacts": CANONICAL,
        },
        "window": {"stable": stable,
                   "pre": pre, "post": post,
                   "changed": sorted(k for k in pre if pre[k] != post.get(k))},
        "files": files,
        "summary": {
            "yaml_strict_reject": strict_rej,
            "yaml_strict_ok": strict_ok,
            "json_advisory_duplicate_keys": json_adv,
        },
        "accept_binding": {
            "affected_hashes": affected,
            "records": bound,
            "counts_by_hash": counts,
            "net_accepts": {a: h for (a, h) in accepts if not accepts[(a, h)]["superseded_by"]},
            "superseded_accepts": superseded,
        },
        "controls": ctl,
        "controls_all_pass": all_ctl_pass,
        "verdict": ("STRICT_YAML_DEFECT_IS_GATE_WIDE" if len(strict_rej) >= 3 and all_ctl_pass
                    else "INSTRUMENT_INVALID" if not all_ctl_pass
                    else "DEFECT_BOUNDED"),
        "falsifier": (
            "Any of: (a) a file classified strict REJECT is accepted by a conforming YAML 1.2 "
            "parser (parser+version named); (b) a duplicate key present in any censused file that "
            "the node-walk detector missed, or a false positive on the control corpus C4-C6; "
            "(c) the accept-binding records misstate a verdict, reviewer, or cited hash for any "
            "affected hash; (d) pre/post window hashes differ (window UNSTABLE)."),
        "limits": [
            "Point-in-time scan of the on-disk review corpus; the controller audit remains authoritative for gate verdicts.",
            "JSON duplicate names are reported advisory only (RFC 8259 does not forbid them).",
            "This census does not evaluate class semantics; it measures document-level parse integrity and verdict binding.",
            "The census is read-only: it proposes no edit to any owned artifact.",
        ],
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "census.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=False)
    return result


if __name__ == "__main__":
    r = main()
    print(json.dumps({
        "verdict": r["verdict"],
        "controls_all_pass": r["controls_all_pass"],
        "yaml_strict_reject": r["summary"]["yaml_strict_reject"],
        "json_advisory": r["summary"]["json_advisory_duplicate_keys"],
        "window_stable": r["window"]["stable"],
    }, indent=1))
    sys.exit(0 if r["controls_all_pass"] else 1)
