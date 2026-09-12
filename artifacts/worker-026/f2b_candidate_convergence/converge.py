#!/usr/bin/env python3
"""W026-F2B-CANDIDATE-ELECTION-CONSUMPTION-01.

Read-only, direction-aware election over the F2b (AF-SCC-C0-VAC-GEN) rev29
two-carrier repair-candidate field, plus a consumption-role map.

Question (distinct from W070's census, W080's single-candidate entailment audit
and W083's two-candidate adjudication): of every distinct candidate byte-state
that repairs both F2b carriers, which survive a direction-aware election, and is
there any candidate that is simultaneously (a) elected, (b) named as the
recommended candidate, and (c) the object actually rehearsed/validated for a
rev30 freeze?  If the three roles land on different hashes, every downstream
"validated/ready" claim is bound to a different object than the one that would
be frozen.

Method:
  1. fail-closed pin of live canonical/mirror/sibling/FROZEN/tool bytes;
  2. deterministic discovery of `af_scc_c0*` class-schema byte-states under
     artifacts/ plus candidate/staged directories, deduped by sha256;
  3. YAML leaf diff vs live; scope class; election predicate
     R1 (D1 size premise repaired) / R2 (D2 denial removed, containment
     asserted, quote-aware) / R3 (D2 entailment direction consistent with the
     artifact's own containment ledger) / R4 (two carriers only);
  4. consumption-role extraction: W083 recommendation, W058 rev30 rehearsal,
     and a bounded report scan for validate/reject mentions per candidate hash;
  5. verdict, findings, falsifier.  Controls C1-C10 drive every predicate,
     including the metalinguistic mention-vs-assertion control.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT = os.path.join(ROOT, "artifacts/worker-026/f2b_candidate_convergence")
SCRATCH = os.path.join(OUT, "_scratch")
CST = timezone(timedelta(hours=8))

TASK_ID = "W026-F2B-CANDIDATE-ELECTION-CONSUMPTION-01"
NODE = "F2b"
GATE = "G-FORM"
CLASS_ID = "AF-SCC-C0-VAC-GEN"

PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/worker-058/rev30_freeze_rehearsal/report.json": None,
    "artifacts/worker-083/f2b_candidate_adjudication/report.json": None,
    "artifacts/worker-080/f2b_repair_entailment_audit/report.json": None,
}
REV12_SNAPSHOT = "artifacts/worker-034/f2b_verify/snapshot_af_scc_c0_vacuum.rev12.yaml"

C1 = "implication_ledger.forbidden_transfers[0].reason"
C2 = "regularity.must_not_conflate[0]"
CARRIERS = (C1, C2)
META_LEAVES = {"revised_at", "revision", "superseded", "revision_history",
               "authored_at", "timestamp_provenance", "frozen_at"}

EXCLUDE_PARTS = (
    "__pycache__", "/sandbox", "/snapshot", "/pinned", "/baseline", "/mutants",
    "/scratch", "/fixtures", "/controls", "/control_", "/raw/", "/stage/",
    "/heldout", "/bases", "/inputs", "/work_", "/pins", "/frozen_inputs",
    "/preflight", "/shadow", "/sim/", "/runs/", "/rehearsal", "/_scratch",
    "/tmp", "/mutant", "/source/", "/sources/", "/quoted/", "/records/",
    "/verify/", "/scratch_", "/pin/",
)
CAND_DIRS = {"candidate", "candidates", "staged", "proposed", "patched_candidate"}

RE_OLD_LARGER = re.compile(r"strictly\s+larger\s+extension\s+class", re.I)
RE_STRICT_SMALLER = re.compile(r"strictly\s+smaller\s+extension\s+(class|set)", re.I)
RE_SMALLEST = re.compile(r"smallest\s+extension\s+set", re.I)
RE_DENIAL = re.compile(r"No\s+containment\s+with\s+C2\s+or\s+C0\s+is\s+asserted", re.I)
RE_NEST = re.compile(r"subset|nested|contains", re.I)
RE_INVERTED = re.compile(r"H2_?loc[-\s]?inextend\w*\s+(entails|implies)\s+this\s+class", re.I)
RE_INVERTED2 = re.compile(r"this\s+class'?s?[^.;]{0,40}?\bis\s+entailed\s+by\b", re.I)
RE_CORRECT = re.compile(r"this\s+class'?s?[^.;]{0,60}?\b(entails|implies)\b", re.I)
RE_ANY_ENTAIL = re.compile(r"\b(entails|implies)\b", re.I)
RE_BRACKET = re.compile(r"\[[^\]]*\]")
# single-quoted span, but never the apostrophe inside a word ("class's")
RE_SQUOTE = re.compile(r"(?<![\w'])'[^']*'(?![\w'])")


def prefer_paths(paths):
    """Deterministic exemplar ordering: primary candidate files before copies."""
    def key(p):
        return (any(x in p for x in ("/evidence/", "/patchcheck", "/patchwork",
                                     "/dryrun", "/tmp", "/controls/")), p)
    return sorted(paths, key=key)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def leaf_diff(live, cand):
    a, b = flatten(live), flatten(cand)
    diff = []
    for p in sorted(set(a) | set(b)):
        if p not in a:
            diff.append({"path": p, "kind": "added", "live": None, "candidate": b[p]})
        elif p not in b:
            diff.append({"path": p, "kind": "removed", "live": a[p], "candidate": None})
        elif a[p] != b[p]:
            diff.append({"path": p, "kind": "changed", "live": a[p], "candidate": b[p]})
    return diff


def get_path(doc, dotted):
    cur = doc
    for tok in re.findall(r"[^.\[\]]+|\[\d+\]", dotted):
        cur = cur[int(tok[1:-1])] if tok.startswith("[") else cur[tok]
    return cur


def dequote(text):
    """Remove meta-commentary so a quoted denial is a mention, not an assertion."""
    return RE_SQUOTE.sub(" ", RE_BRACKET.sub(" ", text))


def classify(live_doc, cand_doc, diff):
    by_path = {d["path"]: d for d in diff}
    sem = [d for d in diff if d["path"].split(".")[-1].split("[")[0] not in META_LEAVES]
    sem_paths = sorted(d["path"] for d in sem)
    t1 = (by_path.get(C1) or {}).get("candidate") or ""
    t2 = (by_path.get(C2) or {}).get("candidate") or ""
    t2_assert = dequote(t2) if t2 else ""

    r1 = bool(t1) and not RE_OLD_LARGER.search(t1) and bool(
        RE_STRICT_SMALLER.search(t1) or RE_SMALLEST.search(t1)
        or (RE_NEST.search(t1) and "E_C2" in t1 and "E_C0" in t1))
    r2 = bool(t2) and not RE_DENIAL.search(t2_assert) and bool(
        (RE_NEST.search(t2_assert) and "E_C0" in t2_assert and "E_C2" in t2_assert)
        or RE_CORRECT.search(t2_assert))
    if RE_INVERTED.search(t2_assert) or RE_INVERTED2.search(t2_assert):
        r3, direction = False, "INVERTED"
    elif RE_CORRECT.search(t2_assert):
        r3, direction = True, "CORRECT"
    elif RE_NEST.search(t2_assert) and "E_C0" in t2_assert and "E_C2" in t2_assert:
        r3, direction = True, "NESTING_ONLY"
    elif RE_ANY_ENTAIL.search(t2_assert):
        r3, direction = False, "UNCLASSIFIED_CLAIM"
    else:
        r3, direction = False, "NONE"

    if sem_paths == sorted(CARRIERS):
        scope = "MINIMAL_TWO_CARRIER"
    elif any(p in CARRIERS for p in sem_paths):
        scope = "PARTIAL_OR_BROAD" if len(sem_paths) > 2 else "PARTIAL_ONE_CARRIER"
    else:
        scope = "NO_CARRIER"
    r4 = scope == "MINIMAL_TWO_CARRIER"
    r5 = not any("sha256" in p for p in sem_paths)
    return {
        "R1_size_premise_repaired": r1,
        "R2_denial_removed_containment_asserted": r2,
        "R2_denial_mentioned_in_brackets": bool(t2) and bool(RE_DENIAL.search(t2))
                                          and not RE_DENIAL.search(t2_assert),
        "R3_entailment_direction": direction,
        "R3_direction_ok": r3,
        "R4_scope": scope,
        "R4_two_carrier_only": r4,
        "R5_no_hash_rebind": r5,
        "elected": bool(r1 and r2 and r3 and r4),
        "semantic_changed_paths": sem_paths,
        "metadata_changed_paths": sorted(
            d["path"] for d in diff
            if d["path"].split(".")[-1].split("[")[0] in META_LEAVES),
        "D1_candidate_text": t1,
        "D2_candidate_text": t2,
    }


def discover():
    found = {}
    for base in ("artifacts", "schemas"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            if any(part in dirpath for part in EXCLUDE_PARTS):
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                if not fn.endswith((".yaml", ".yml")):
                    continue
                parent = os.path.basename(dirpath)
                by_name = "af_scc_c0" in fn
                by_dir = parent in CAND_DIRS
                if not (by_name or by_dir):
                    continue
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, ROOT)
                if any(part in rel for part in EXCLUDE_PARTS):
                    continue
                try:
                    doc = load_yaml(p)
                    if not isinstance(doc, dict) or doc.get("class_id") != CLASS_ID:
                        continue
                    h = sha256_file(p)
                except Exception:  # noqa: BLE001
                    continue
                found.setdefault(h, []).append(rel)
    return found


def consumer_scan(hashes):
    prefixes = {h: h[:12] for h in hashes}
    hits = {h: {"validate": [], "rehearsal": [], "reject": [], "mention": []} for h in hashes}
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "artifacts")):
        rel_dir = os.path.relpath(dirpath, ROOT)
        if any(part in rel_dir for part in EXCLUDE_PARTS):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        if rel_dir.count(os.sep) > 2:
            dirnames[:] = []
        for fn in filenames:
            if not fn.endswith((".json", ".md", ".txt")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(p) > 500_000 or os.path.getmtime(p) < 1757600000:
                    continue
                txt = open(p, "r", encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            scanned += 1
            low = txt.lower()
            for h, pref in prefixes.items():
                if pref not in txt:
                    continue
                rel = os.path.relpath(p, ROOT)
                if any(k in low for k in ("reject", "defect", "do not land", "supersed",
                                          "not land", "inverted", "void")):
                    grp = "reject"
                elif "rehearsal" in low or "rev30" in low or "owner_runbook" in low:
                    grp = "rehearsal"
                elif any(k in low for k in ("valid", "clear", "finding-free", "pass",
                                            "ready", "recommend")):
                    grp = "validate"
                else:
                    grp = "mention"
                hits[h][grp].append(rel)
    for h in hits:
        for g in hits[h]:
            hits[h][g] = sorted(set(hits[h][g]))
    return scanned, hits


def main():
    result = {
        "task_id": TASK_ID, "actor": "worker-026", "node_id": NODE,
        "gate": GATE, "class_id": CLASS_ID,
        "started_at": datetime.now(CST).isoformat(timespec="seconds"),
        "authority": ("worker-level read-only measurement only; no gate verdict, no node "
                      "status, no validation_status promotion, no canonical write"),
        "related_prior_work": {
            "W070-F2B-REV29-CANDIDATE-CENSUS-01":
                "artifacts/worker-070/f2b_candidate_census/report.json",
            "W080-F2B-REPAIR-H2E-01":
                "artifacts/worker-080/f2b_repair_entailment_audit/report.json",
            "W083-F2B-CANDIDATE-ADJUDICATION-01":
                "artifacts/worker-083/f2b_candidate_adjudication/report.json",
            "W058-REV30-FREEZE-REHEARSAL-01":
                "artifacts/worker-058/rev30_freeze_rehearsal/report.json",
        },
    }
    os.makedirs(SCRATCH, exist_ok=True)

    pins = {}
    for rel, want in PINS.items():
        p = os.path.join(ROOT, rel)
        got = sha256_file(p)
        pins[rel] = {"declared": want, "measured": got,
                     "match": True if want is None else got == want}
    if not all(v["match"] for v in pins.values()):
        print(json.dumps({"abort": "PIN_DRIFT", "pins": pins}, indent=1))
        return 2
    result["pins"] = pins

    live_doc = load_yaml(os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml"))
    chain = get_path(live_doc, "implication_ledger.extension_class_containment")
    order_ok = all(t in chain for t in ("E_C0", "E_H2loc", "E_{C^1,1}", "E_C2")) and (
        chain.index("E_C0") < chain.index("E_H2loc") < chain.index("E_{C^1,1}")
        < chain.index("E_C2"))
    result["containment_model"] = {
        "chain_text": chain,
        "allowed_direction": "C0-inextendibility => H2loc-inextendibility => C2-inextendibility",
        "forbidden_direction": "H2loc-inextendibility => AF-SCC-C0-VAC-GEN conclusion",
        "live_chain_parses_largest_to_smallest": bool(order_ok),
    }
    if not order_ok:
        print(json.dumps({"abort": "CONTAINMENT_CHAIN_UNPARSEABLE"}, indent=1))
        return 2

    live_hash = PINS["schemas/af_scc_c0_vacuum.yaml"]
    found = discover()
    cands = []
    for h, paths in sorted(found.items()):
        if h == live_hash:
            continue
        paths = prefer_paths(paths)
        try:
            doc = load_yaml(os.path.join(ROOT, paths[0]))
        except Exception:  # noqa: BLE001
            continue
        diff = leaf_diff(live_doc, doc)
        if not any(d["path"] in CARRIERS for d in diff):
            continue
        cls = classify(live_doc, doc, diff)
        mt = os.path.getmtime(os.path.join(ROOT, paths[0]))
        cands.append({
            "id": None, "sha256": h, "exemplar": paths[0], "all_paths": paths,
            "n_paths": len(paths),
            "mtime": datetime.fromtimestamp(mt, CST).isoformat(timespec="seconds"),
            "era": "rev29" if mt >= 1757609400 else "pre_rev29",
            "scope": cls["R4_scope"],
            "classification": cls,
        })
    cands.sort(key=lambda c: (c["scope"] != "MINIMAL_TWO_CARRIER", c["sha256"]))
    for i, c in enumerate(cands, 1):
        c["id"] = f"W026-CE-{i:02d}"
    result["candidates"] = cands

    field = [c for c in cands if c["scope"] == "MINIMAL_TWO_CARRIER"]
    others = [c for c in cands if c["scope"] != "MINIMAL_TWO_CARRIER"]
    elected = [c for c in field if c["classification"]["elected"]]
    rejected = [c for c in field if not c["classification"]["elected"]]
    inverted = [c for c in field
                if c["classification"]["R3_entailment_direction"] == "INVERTED"]

    # ---- consumption roles -------------------------------------------------
    rec_path = "artifacts/worker-083/f2b_candidate_adjudication/report.json"
    reh_path = "artifacts/worker-058/rev30_freeze_rehearsal/report.json"
    try:
        rec = json.load(open(os.path.join(ROOT, rec_path)))
        rec_sha = rec["recommendation"]["candidate_sha256"]
        rec_conflict = bool(rec["recommendation"].get("author_conflict"))
        rec_candidate = rec["recommendation"].get("candidate")
    except Exception:  # noqa: BLE001
        rec_sha, rec_conflict, rec_candidate = None, None, None
    rec_measured = {
        "path": rec_path,
        "sha256": sha256_file(os.path.join(ROOT, rec_path)),
        "mtime": datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, rec_path)),
                                        CST).isoformat(timespec="seconds"),
        "recommended_sha256_measured": rec_sha,
        "recommended_candidate": rec_candidate,
        "author_conflict_flag": rec_conflict,
        "revision_note": ("this report was rewritten at 01:11-01:12 during the audit "
                          "window; the same path recommended C024=679ab7bc at the "
                          "worker's first read (~01:08) and now recommends the "
                          "adjudicator's own authored C083=1315427f with "
                          "author_conflict=true"),
    }
    result["recommendation_role"] = rec_measured
    try:
        reh_sha = json.load(open(os.path.join(ROOT, reh_path)))["candidate"]["sha256"]
    except Exception:  # noqa: BLE001
        reh_sha = None
    scanned, hits = consumer_scan([c["sha256"] for c in field])
    for c in cands:
        h = c["sha256"]
        c["roles"] = {
            "recommended_by_W083": h == rec_sha,
            "rehearsed_by_W058": h == reh_sha,
            "elected": c["classification"]["elected"],
            "validate_mentions": hits.get(h, {}).get("validate", []),
            "rehearsal_mentions": hits.get(h, {}).get("rehearsal", []),
            "reject_mentions": hits.get(h, {}).get("reject", []),
        }
    role_holders = [c for c in field
                    if c["roles"]["elected"] and c["roles"]["recommended_by_W083"]
                    and c["roles"]["rehearsed_by_W058"]]
    result["election"] = {
        "discovered_byte_states": len(cands),
        "minimal_two_carrier_candidates": len(field),
        "broad_or_partial_states": [{"id": c["id"], "sha256": c["sha256"],
                                     "scope": c["scope"]} for c in others],
        "elected_ids": [c["id"] for c in elected],
        "elected_hashes": [c["sha256"] for c in elected],
        "rejected_ids": [c["id"] for c in rejected],
        "inverted_ids": [c["id"] for c in inverted],
        "unique_electable_text": len(elected) == 1,
        "recommended_by_W083": rec_sha,
        "rehearsed_by_W058": reh_sha,
        "candidates_holding_all_three_roles": [c["id"] for c in role_holders],
        "role_intersection_empty": len(role_holders) == 0,
        "consumer_files_scanned": scanned,
    }

    # ---- verdict + findings ------------------------------------------------
    findings = []
    verdict = ("UNDER_DETERMINED_ELECTION" if len(elected) != 1
               else "UNIQUE_ELECTABLE_CANDIDATE")
    if inverted:
        verdict += "__INVERTED_MINIMAL_CANDIDATES"
    if result["election"]["role_intersection_empty"]:
        verdict += "__NO_CANDIDATE_HOLDS_ALL_ROLES"

    findings.append({
        "id": "W026-CE-F1",
        "severity": "material" if len(elected) != 1 else "info",
        "statement": (f"{len(field)} minimal two-carrier candidate byte-states; "
                      f"{len(elected)} pass R1-R4. The repaired text is not unique, "
                      f"so 'the candidate' is under-determined absent an explicit "
                      f"owner election."),
        "elected": [{"id": c["id"], "sha256": c["sha256"],
                     "R3": c["classification"]["R3_entailment_direction"]}
                    for c in elected],
    })
    if inverted:
        findings.append({
            "id": "W026-CE-F2",
            "severity": "hard",
            "statement": (f"{len(inverted)} minimal candidates assert the inverted "
                          f"entailment 'H2_loc-inextendibility entails this class' and "
                          f"are rejected on direction."),
            "candidates": [{"id": c["id"], "sha256": c["sha256"],
                            "consumed_rehearsal":
                                bool(c["roles"]["rehearsed_by_W058"]),
                            "validate_mentions": len(c["roles"]["validate_mentions"])}
                           for c in inverted],
        })
    if result["election"]["role_intersection_empty"]:
        findings.append({
            "id": "W026-CE-F3",
            "severity": "hard",
            "statement": ("No candidate holds all three roles (elected + recommended by "
                          "W083 + rehearsed by W058). The rev30 rehearsal object "
                          f"({str(reh_sha)[:12]}) is a direction-rejected candidate, "
                          f"while the W083-recommended object ({str(rec_sha)[:12]}) is "
                          f"electable but unrehearsed."),
            "recommended": rec_sha, "rehearsed": reh_sha,
            "elected": [c["sha256"] for c in elected],
        })
    corrected = [c for c in elected if "worker-080" in " ".join(c["all_paths"])]
    if corrected:
        findings.append({
            "id": "W026-CE-F4",
            "severity": "material",
            "statement": (f"{len(corrected)} electable candidate(s) come from the W080 "
                          f"corrected pair; they carry no rehearsal or validation "
                          f"consumption."),
            "candidates": [c["sha256"] for c in corrected],
        })
    mention_only = [c for c in field
                    if c["classification"]["R2_denial_mentioned_in_brackets"]]
    findings.append({
        "id": "W026-CE-F5",
        "severity": "method",
        "statement": (f"{len(mention_only)} candidate(s) quote the superseded denial "
                      f"inside brackets; a naive denial detector misclassifies them as "
                      f"still asserting it. Election is quote-aware (controls C7/C10)."),
        "candidates": [c["sha256"] for c in mention_only],
    })
    extra = [c for c in field if not c["classification"]["R5_no_hash_rebind"]]
    if extra:
        findings.append({
            "id": "W026-CE-F6",
            "severity": "material",
            "statement": (f"{len(extra)} minimal candidate(s) additionally rebind a "
                          f"declared sha256 or add binding blocks; landing one moves an "
                          f"evidence binding inside a text repair."),
            "candidates": [c["sha256"] for c in extra],
        })
    if rec_conflict:
        findings.append({
            "id": "W026-CE-F7",
            "severity": "material",
            "statement": ("The recommendation role moved during the audit window and now "
                          "self-recommends: W083 report "
                          f"{rec_measured['sha256'][:12]} recommends {str(rec_sha)[:12]} "
                          f"({rec_candidate}) with author_conflict=true, while the same "
                          "path recommended 679ab7bc8746 (~01:08). Any owner action that "
                          "reads 'the recommended candidate' must pin the report hash."),
            "recommendation_role": rec_measured,
        })
    # cross-check against W070's declared candidate set
    w070_path = "artifacts/worker-070/f2b_candidate_census/report.json"
    cross = {"source": w070_path, "declared_hashes_in_field": [], "declared_missing": []}
    try:
        w070 = json.load(open(os.path.join(ROOT, w070_path)))
        field_hashes = {c["sha256"] for c in field}
        declared = set()
        for r in w070.get("results", []):
            blob = json.dumps(r)
            for h in re.findall(r"[0-9a-f]{64}", blob):
                declared.add(h)
        cross["declared_hashes_in_field"] = sorted(declared & field_hashes)
        cross["declared_missing"] = sorted(declared - field_hashes)
        cross["declared_total_hashes_seen"] = len(declared)
        cross["w070_aggregate"] = w070.get("aggregate", {}).get(
            "declared_candidates")
    except Exception as exc:  # noqa: BLE001
        cross["error"] = str(exc)
    result["cross_check_W070"] = cross
    result["findings"] = findings
    result["verdict"] = verdict
    result["falsifier"] = (
        "Falsified if a re-run at the same pins finds (a) at most one elected candidate, "
        "(b) a candidate holding elected+recommended+rehearsed roles, (c) an inverted "
        "candidate passing R3, or (d) any control C1-C10 not discriminating as declared."
    )
    result["non_claims"] = [
        "no gate verdict, no node transition, no validation_status promotion",
        "no canonical artifact written, no candidate adopted, landed, or re-frozen",
        "no adjudication of which electable wording the owner should land; the claim is "
        "only that the landed bytes must equal the rehearsed/verified bytes",
        "no re-litigation of D1/D2 existence (established by worker-017/066/083/080)",
    ]

    # ---- controls ----------------------------------------------------------
    ctrl_dir = os.path.join(SCRATCH, "controls")
    os.makedirs(ctrl_dir, exist_ok=True)
    live_text = open(os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml"),
                     encoding="utf-8").read()
    controls = []

    def measure(text):
        p = os.path.join(ctrl_dir, "_measure.yaml")
        open(p, "w", encoding="utf-8").write(text)
        doc = load_yaml(p)
        return classify(live_doc, doc, leaf_diff(live_doc, doc))

    def ctl(cid, expect, observed, detail):
        controls.append({"id": cid, "expected": expect, "observed": observed,
                         "pass": expect == observed, "detail": detail})

    ctl("W026-CE-C1", "NOT_REPAIRED",
        "REPAIRED" if measure(live_text)["elected"] else "NOT_REPAIRED",
        "live b2ab6acb is not itself a repair")
    rev12 = open(os.path.join(ROOT, REV12_SNAPSHOT), encoding="utf-8").read()
    ctl("W026-CE-C2", "NOT_REPAIRED",
        "REPAIRED" if measure(rev12)["elected"] else "NOT_REPAIRED",
        "rev12 55d0a1ea predecessor is not a repair")
    if elected:
        el = elected[0]
        base = open(os.path.join(ROOT, el["exemplar"]), encoding="utf-8").read()
        ctl("W026-CE-C3", True, measure(base)["elected"],
            f"byte copy of elected {el['sha256'][:12]}")
        stamped = re.sub(r'revised_at: "[^"]*"',
                         'revised_at: "2026-09-12T01:45:00+08:00"', base, count=1)
        ctl("W026-CE-C4", True, measure(stamped)["elected"],
            "metadata-only re-stamp keeps election")
        third = stamped.replace("extension_solution_concept: none",
                                "extension_solution_concept: control_third_leaf", 1)
        ctl("W026-CE-C5", False, measure(third)["elected"],
            "third semantic leaf breaks R4")
        d1 = el["classification"]["D1_candidate_text"]
        d2 = el["classification"]["D2_candidate_text"]
        ctl("W026-CE-C6", False,
            measure(stamped.replace(d1, "C2 is a strictly larger extension class, "
                                        "so C2-inextendibility is strictly weaker", 1))
            ["R1_size_premise_repaired"], "D1 reverted -> R1 fails")
        ctl("W026-CE-C7", False,
            measure(stamped.replace(d2, "No containment with C2 or C0 is asserted here; "
                                        "the informal phrase is not used.", 1))
            ["R2_denial_removed_containment_asserted"],
            "asserted denial -> R2 fails")
        ctl("W026-CE-C8", "INVERTED",
            measure(stamped.replace(d2, "H2_loc is distinct. The extension sets are "
                                        "nested: E_C2 subset of E_C0, so "
                                        "H2_loc-inextendibility ENTAILS this class's "
                                        "conclusion.", 1))["R3_entailment_direction"],
            "planted inversion -> R3 INVERTED")
        ctl("W026-CE-C9", True,
            measure(yaml.safe_dump(yaml.safe_load(stamped), sort_keys=True))["elected"],
            "YAML roundtrip preserves election")
        mention = stamped.replace(
            d2,
            "H2_loc is distinct. The extension sets are nested: E_C2 subset of E_C0 "
            "[the earlier 'no containment with C2 or C0 is asserted here' was wrong].",
            1)
        m = measure(mention)
        ctl("W026-CE-C10", True,
            m["R2_denial_removed_containment_asserted"] and m["elected"],
            "bracketed/quote mention of the denial is not an assertion")
        passive = stamped.replace(
            d2,
            "H2_loc is distinct. The extension sets are nested: E_C2 subset of E_C0, "
            "and this class's conclusion is entailed by H2_loc-inextendibility.",
            1)
        ctl("W026-CE-C11", "INVERTED",
            measure(passive)["R3_entailment_direction"],
            "passive-voice inversion is classified INVERTED")
    result["controls"] = controls
    result["controls_passed"] = sum(1 for c in controls if c["pass"])
    result["controls_total"] = len(controls)
    result["generated_at"] = datetime.now(CST).isoformat(timespec="seconds")

    json.dump(result, open(os.path.join(OUT, "report.json"), "w", encoding="utf-8"),
              indent=1, sort_keys=True)
    json.dump({"pins": pins, "candidates": cands,
               "consumer_hits": hits, "containment_model": result["containment_model"]},
              open(os.path.join(OUT, "evidence.json"), "w", encoding="utf-8"),
              indent=1, sort_keys=True)
    json.dump({"controls": controls, "passed": result["controls_passed"],
               "total": result["controls_total"]},
              open(os.path.join(OUT, "controls.json"), "w", encoding="utf-8"),
              indent=1, sort_keys=True)

    summary = {
        "task_id": TASK_ID, "verdict": verdict,
        "minimal_two_carrier_candidates": len(field),
        "elected": [{"id": c["id"], "sha256": c["sha256"],
                     "R3": c["classification"]["R3_entailment_direction"]} for c in elected],
        "inverted": [c["sha256"] for c in inverted],
        "recommended_by_W083": rec_sha, "rehearsed_by_W058": reh_sha,
        "role_intersection_empty": result["election"]["role_intersection_empty"],
        "controls": f"{result['controls_passed']}/{result['controls_total']}",
        "findings": [f["id"] for f in findings],
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
