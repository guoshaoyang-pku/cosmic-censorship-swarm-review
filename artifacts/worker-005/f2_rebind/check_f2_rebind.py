#!/usr/bin/env python3
"""worker-005 independent F2 re-bind / class-separation audit.

Scope: node F2, classes AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN, gate G-FORM.
This is an *independent* re-implementation of the separation lint, not a copy of
artifacts/worker-05/check_f2_integration.py. It consumes artifacts/worker-06/class_binding_rules.json
as the sibling class-id / composite-pattern hypothesis (per assignment astra-adj1-05-assignment)
and the frozen binding gate artifacts/formulation/tools/check_class_schema.py (FORM-RULE-SPEC v1.1).

What it decides (structural / evidence only; it decides no mathematics):

  Aggregator (schemas/af_scc_regularities.yaml is an INDEX, not a class schema)
    A1 identity        node F2, formulation_aggregator, unverified, no completion claim
    A2 component-set   exactly the two SCC class ids, once each, separate entries with roles
    A3 component-pins  path + 64-hex sha256; report mode: pinned hash equals file on disk
    A4 class-id-join   no value joins the two class ids with a separator/disjunction
    A5 composite-reg   no composite regularity token (w06 patterns) anywhere in the index
    A6 no-conclusion   no conclusion/conclusion_type object and no extension statement
    A7 no-alias        no anchors, aliases or merge keys
  Components (report mode)
    B1 identity        class_id matches the aggregator entry and node under F2
    B2 selector        class_components.regularity_token is the entry's own selector
    B3 conclusion      conclusion subtree non-empty, family-separated; sibling conclusions distinct
    B4 composite       frozen gate R13 on the component (raw mentions reported as mentions only)
    B5 binding-gate    frozen canonical gate verdict
  Evidence hygiene (report mode, orthogonal to separation)
    H1 duplicate keys  any mapping key repeated (silent last-wins is an evidence hazard)
    H2 future-dated    any ISO timestamp later than the measured instant + tolerance
    H3 pin annotation  pin evidence claims a time inconsistent with the pinned file's mtime

Fixture mode replays artifacts/worker-05/fixtures_f2/*.yaml against _meta.expected, and runs
always-accept / always-reject null controls.  --selftest plants 6 mutants into the live index
and asserts the expected invariant fires and that the unmutated index passes A1-A7.

A verdict here is this worker's measurement, not a gate verdict; worker events cannot set
status=done, validation_status=passed, or a gate verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
AGG = ROOT / "schemas" / "af_scc_regularities.yaml"
COMPONENTS = {
    "AF-SCC-C2-VAC-GEN": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
}
RULES_PATH = ROOT / "artifacts" / "worker-06" / "class_binding_rules.json"
CANON = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
AUTHOR_LINT = ROOT / "artifacts" / "worker-05" / "check_f2_integration.py"
FIXTURES = ROOT / "artifacts" / "worker-05" / "fixtures_f2"
SCC_CLASSES = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
SELECTOR = {"AF-SCC-C2-VAC-GEN": "C2", "AF-SCC-C0-VAC-GEN": "C0"}

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
TS_RE = re.compile(
    r"(20\d{2}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)
ANCHOR_DEF_RE = re.compile(r"(?:^|[\s\[{,])(&[A-Za-z0-9_-]+)")
ALIAS_USE_RE = re.compile(r"(?:^|[\s\[{,])(\*[A-Za-z0-9_-]+)")
MERGE_RE = re.compile(r"<<\s*:")
CONCLUSION_KEYS = {"conclusion", "conclusion_type"}
EXTENSION_RE = re.compile(r"inextendib\w*", re.I)
RELATION_PATH_RE = re.compile(
    r"relation|related|implication|sibling|contrast|disjoint|forbidden|must_not|"
    r"anti_scope|prohibited|excluded|mention|prohibition",
    re.I,
)
FUTURE_TOLERANCE_S = 120


# ----------------------------------------------------------------------------- yaml tracking
class TrackingLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate keys, anchor definitions and alias uses."""

    def __init__(self, stream):
        super().__init__(stream)
        self.dup_keys: list[tuple[str, int]] = []
        self.anchor_defs: list[str] = []
        self.alias_uses: list[str] = []

    def compose_node(self, parent, index):  # type: ignore[override]
        if self.check_event(yaml.events.AliasEvent):
            self.alias_uses.append(self.peek_event().anchor)
        node = super().compose_node(parent, index)
        if getattr(node, "anchor", None):
            self.anchor_defs.append(node.anchor)
        return node

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        counts: dict[str, int] = {}
        for key_node, _ in node.value:
            try:
                key = self.construct_object(key_node, deep=deep)
            except Exception:
                continue
            counts[str(key)] = counts.get(str(key), 0) + 1
        for key, n in counts.items():
            if n > 1:
                self.dup_keys.append((key, n))
        return super().construct_mapping(node, deep=deep)


def load_tracked(text: str) -> tuple[object, dict]:
    loader = TrackingLoader(text)
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    meta = {
        "dup_keys": loader.dup_keys,
        "anchor_defs": loader.anchor_defs,
        "alias_uses": loader.alias_uses,
        "merge_keys": MERGE_RE.findall(text),
    }
    return doc, meta


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def parse_ts(value: str) -> datetime | None:
    v = value.strip().replace(" ", "T")
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    if re.match(r"^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:?\d{2})?$", v):
        if v.endswith(("Z",)) or re.search(r"[+-]\d{2}:?\d{2}$", v):
            pass
        elif len(v) == 16:
            v += ":00"
        if not re.search(r"[+-]\d{2}:?\d{2}$", v):
            v += "+08:00"
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            return None
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text())


def walk(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, x


def key_paths(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            yield p
            yield from key_paths(v, p)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from key_paths(v, f"{prefix}[{i}]")


def joined_class_regex(class_ids: list[str]) -> re.Pattern:
    ids = "|".join(re.escape(c) for c in class_ids)
    sep = r"\s*(?:[;/,|&+]|\band\b|\bor\b|\bwith\b)\s*"
    return re.compile(rf"(?:{ids}){sep}(?:{ids})", re.I)


def first_context(raw: str, needle: str, width: int = 110) -> str:
    low = needle.lower()
    for line in raw.splitlines():
        if low in line.lower():
            return line.strip()[:width]
    return ""


def find_future_timestamps(raw: str, now: datetime) -> list[dict]:
    out = []
    for i, line in enumerate(raw.splitlines(), start=1):
        for m in TS_RE.finditer(line):
            t = parse_ts(m.group(1))
            if t is None:
                continue
            if (t - now).total_seconds() > FUTURE_TOLERANCE_S:
                out.append({"value": m.group(1), "line": i, "text": line.strip()[:110]})
    return out


# ----------------------------------------------------------------------------- aggregator checks
def check_aggregator(doc, raw: str, meta: dict, rules: dict, *, fixture: bool, now: datetime,
                     disk: bool = True) -> list[dict]:
    F: list[dict] = []

    def add(fid, verdict, detail):
        F.append({"id": fid, "verdict": verdict, "detail": detail})

    def ok(fid, detail):
        add(fid, "pass", detail)

    def bad(fid, detail):
        add(fid, "fail", detail)

    comps = doc.get("components") if isinstance(doc, dict) else None
    if not isinstance(comps, list):
        comps = []

    # A1 identity / state
    problems = []
    if not isinstance(doc, dict):
        problems.append("document is not a mapping")
    else:
        if str(doc.get("node_id")) != "F2":
            problems.append(f"node_id={doc.get('node_id')!r}")
        if str(doc.get("artifact_type")) != "formulation_aggregator":
            problems.append(f"artifact_type={doc.get('artifact_type')!r}")
        if not fixture:
            if str(doc.get("validation_status")) != "unverified":
                problems.append(f"validation_status={doc.get('validation_status')!r}")
            if doc.get("claims_completion") is not False:
                problems.append(f"claims_completion={doc.get('claims_completion')!r}")
    bad("A1-identity", "; ".join(problems)) if problems else ok(
        "A1-identity", "node F2, formulation_aggregator" + ("" if fixture else ", unverified, no completion claim"))

    # A2 component set: exactly the two SCC ids, once each, separate entries with roles
    problems = []
    ids = [str(c.get("class_id")) for c in comps if isinstance(c, dict)]
    if sorted(ids) != sorted(SCC_CLASSES):
        problems.append(f"component class ids {ids} != {SCC_CLASSES}")
    for cid in SCC_CLASSES:
        if ids.count(cid) != 1:
            problems.append(f"{cid} appears {ids.count(cid)}x")
    if not all(isinstance(c, dict) and c.get("role") for c in comps):
        problems.append("a component entry lacks a role")
    if len(comps) != 2:
        problems.append(f"{len(comps)} component entries, expected 2")
    bad("A2-component-set", "; ".join(problems)) if problems else ok(
        "A2-component-set", f"components = {ids}, separate entries with roles")

    # A3 component pins
    problems = []
    for c in comps:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("class_id"))
        p, sh = str(c.get("path", "")), str(c.get("sha256", ""))
        if not p:
            problems.append(f"{cid}: missing path")
        if not HEX64_RE.match(sh):
            problems.append(f"{cid}: sha256 not 64-hex ({sh[:16]!r})")
            continue
        if disk and not fixture:
            fp = ROOT / p
            if not fp.exists():
                problems.append(f"{cid}: path absent {p}")
            elif sha256_file(fp) != sh:
                problems.append(f"{cid}: disk {sha256_file(fp)[:12]} != pin {sh[:12]}")
    bad("A3-component-pins", "; ".join(problems)) if problems else ok(
        "A3-component-pins", "each component pinned" + ("" if (fixture or not disk) else " and pin == disk"))

    # A4 joined class ids (lexical, whole index)
    all_ids = list(rules.get("classes", {}).keys()) or SCC_CLASSES
    hits = sorted({m.group(0) for m in joined_class_regex(all_ids).finditer(raw)})
    bad("A4-class-id-join", f"joined class-id strings: {hits}") if hits else ok(
        "A4-class-id-join", "no joined class-id string in the index text")

    # A5 composite regularity (lexical, whole index; an index may not even mention a composite)
    hits = []
    for pat in rules.get("composite_regularity_regexes", []):
        hits += [m.group(0) for m in re.finditer(pat, raw, re.I)]
    if hits:
        bad("A5-composite-regularity",
            f"composite regularity strings {hits}; contexts {[first_context(raw, h) for h in hits[:3]]}")
    else:
        ok("A5-composite-regularity", "no composite regularity token in the index text")

    # A6 no conclusion object / extension statement in the index
    key_hits = []
    if isinstance(doc, dict):
        key_hits = [p for p in key_paths(doc) if p.rsplit(".", 1)[-1].split("[")[0] in CONCLUSION_KEYS]
    ext = sorted({m.group(0) for m in EXTENSION_RE.finditer(raw)})
    if key_hits or ext:
        bad("A6-no-conclusion-object", f"conclusion keys={key_hits}, extension tokens={ext}")
    else:
        ok("A6-no-conclusion-object", "index defines no conclusion object and no extension statement")

    # A7 anchors / aliases / merge keys
    anchors = sorted(set(meta.get("anchor_defs", [])) | {m.group(1) for m in ANCHOR_DEF_RE.finditer(raw)})
    aliases = sorted(set(meta.get("alias_uses", [])) | {m.group(1) for m in ALIAS_USE_RE.finditer(raw)})
    merges = meta.get("merge_keys", []) or MERGE_RE.findall(raw)
    if anchors or aliases or merges:
        bad("A7-no-alias", f"anchors={anchors}, alias uses={aliases}, merge keys={merges}")
    else:
        ok("A7-no-alias", "no anchors, aliases or merge keys")

    # evidence hygiene (report mode only)
    if not fixture:
        dup = meta.get("dup_keys", [])
        if dup:
            bad("H1-duplicate-keys", "duplicate mapping keys (last-wins): "
                + ", ".join(f"{k} x{n}" for k, n in dup))
        else:
            ok("H1-duplicate-keys", "no duplicate mapping keys")
        fut = find_future_timestamps(raw, now)
        if fut:
            bad("H2-future-timestamps", "; ".join(f"{f['value']} (line {f['line']})" for f in fut))
        else:
            ok("H2-future-timestamps", f"no timestamp later than {now.isoformat()} + {FUTURE_TOLERANCE_S}s")
    return F


# ----------------------------------------------------------------------------- component checks
def run_canonical(path: Path) -> dict:
    try:
        p = subprocess.run([sys.executable, str(CANON), str(path), "--json"],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        rep = json.loads(p.stdout) if p.stdout.strip() else {}
        return {"verdict": rep.get("verdict"), "failed_rules": rep.get("failed_rules", []),
                "failures": rep.get("failures", []), "exit": p.returncode}
    except Exception as exc:
        return {"verdict": None, "failed_rules": [], "failures": [{"rule": "CANON", "msg": repr(exc)}],
                "exit": None}


def check_components(doc, rules: dict, now: datetime) -> tuple[list[dict], dict]:
    F: list[dict] = []
    loaded: dict[str, dict] = {}

    def add(fid, verdict, detail):
        F.append({"id": fid, "verdict": verdict, "detail": detail})

    def ok(fid, detail):
        add(fid, "pass", detail)

    def bad(fid, detail):
        add(fid, "fail", detail)

    comps = doc.get("components") or []
    entries = {str(c.get("class_id")): c for c in comps if isinstance(c, dict)}
    for cid in SCC_CLASSES:
        path = COMPONENTS[cid]
        raw = path.read_text()
        cdoc, cmeta = load_tracked(raw)
        canon = run_canonical(path)
        loaded[cid] = {"doc": cdoc, "raw": raw, "meta": cmeta, "canon": canon,
                       "sha256": sha256_file(path), "path": str(path.relative_to(ROOT))}
        entry = entries.get(cid, {})

        # B1 identity
        if not isinstance(cdoc, dict):
            bad("B1-identity", f"{cid}: component does not parse as a mapping")
        elif str(cdoc.get("class_id")) != cid:
            bad("B1-identity", f"{cid}: component class_id={cdoc.get('class_id')!r}")
        elif str(entry.get("class_id")) != cid:
            bad("B1-identity", f"{cid}: aggregator entry class_id={entry.get('class_id')!r}")
        elif "F2" not in str(cdoc.get("node_id", "")):
            bad("B1-identity", f"{cid}: node_id={cdoc.get('node_id')!r} not under F2")
        else:
            ok("B1-identity", f"{cid}: component class_id and node {cdoc.get('node_id')} agree with the entry")

        # B2 selector
        tok = (cdoc.get("class_components") or {}).get("regularity_token") if isinstance(cdoc, dict) else None
        if str(tok) != SELECTOR[cid]:
            bad("B2-selector", f"{cid}: regularity_token={tok!r}, expected {SELECTOR[cid]!r}")
        else:
            ok("B2-selector", f"{cid}: selector {tok}")

        # B4 composite: frozen gate R13 decides; raw mentions are reported as mentions
        raw_hits = []
        for pat in rules.get("composite_regularity_regexes", []):
            raw_hits += [m.group(0) for m in re.finditer(pat, raw, re.I)]
        if "R13" in canon.get("failed_rules", []):
            bad("B4-composite", f"{cid}: frozen gate R13 failed")
        else:
            ok("B4-composite", f"{cid}: frozen gate R13 pass"
               + (f"; raw mentions in prohibition/comment text: {sorted(set(raw_hits))}" if raw_hits else ""))

        # B5 frozen binding gate
        if canon.get("verdict") != "pass":
            bad("B5-binding-gate", f"{cid}: canonical verdict={canon.get('verdict')!r} "
                                   f"failed_rules={canon.get('failed_rules')}")
        else:
            ok("B5-binding-gate", f"{cid}: canonical gate pass (FORM-RULE-SPEC v1.1)")

    # B3 conclusion separation across the two components
    def conclusions(cid):
        cdoc = loaded[cid]["doc"]
        if not isinstance(cdoc, dict):
            return None
        sub = cdoc.get("conclusion")
        return " ".join(str(v) for _p, v in walk(sub)) if sub is not None else None

    t2, t0 = conclusions("AF-SCC-C2-VAC-GEN"), conclusions("AF-SCC-C0-VAC-GEN")
    problems = []
    if not t2 or not t0:
        problems.append("a conclusion subtree is missing or empty")
    elif t2.strip() == t0.strip():
        problems.append("conclusions are identical (merged)")
    else:
        if "C2" not in t2:
            problems.append("C2 conclusion carries no C2 token")
        if "C0" not in t0:
            problems.append("C0 conclusion carries no C0 token")
        for cid, other in (("AF-SCC-C2-VAC-GEN", "C0"), ("AF-SCC-C0-VAC-GEN", "C2")):
            cdoc = loaded[cid]["doc"]
            sub = cdoc.get("conclusion") if isinstance(cdoc, dict) else None
            for p, v in walk(sub):
                if re.search(rf"\b{other}\b", str(v)) and not RELATION_PATH_RE.search(p):
                    problems.append(f"{cid}: {other} token outside a relation field at {p}")
    bad("B3-conclusion", "; ".join(problems)) if problems else ok(
        "B3-conclusion", "conclusions non-empty, distinct, family-separated")

    # hygiene per component (reported, orthogonal)
    hy = []
    for cid, info in loaded.items():
        dup = info["meta"].get("dup_keys", [])
        fut = find_future_timestamps(info["raw"], now)
        hy.append({"class_id": cid, "duplicate_keys": [f"{k} x{n}" for k, n in dup],
                   "future_timestamps": [f["value"] for f in fut]})
    return F, {"components": {c: {"path": i["path"], "sha256": i["sha256"],
                                  "canonical": i["canon"]} for c, i in loaded.items()},
               "hygiene": hy}


# ----------------------------------------------------------------------------- fixtures / selftest
def summarise(F: list[dict], ids: list[str] | None = None) -> str:
    sel = [f for f in F if ids is None or f["id"] in ids]
    return "fail" if any(f["verdict"] == "fail" for f in sel) else "pass"


STRUCTURAL_IDS = ["A1-identity", "A2-component-set", "A3-component-pins", "A4-class-id-join",
                  "A5-composite-regularity", "A6-no-conclusion-object", "A7-no-alias"]
HYGIENE_IDS = ["H1-duplicate-keys", "H2-future-timestamps"]


def run_fixtures(rules: dict, now: datetime) -> dict:
    rows = []
    for p in sorted(FIXTURES.glob("*.yaml")):
        raw = p.read_text()
        doc, meta = load_tracked(raw)
        diag = doc.get("_meta", {}) if isinstance(doc, dict) else {}
        F = check_aggregator(doc, raw, meta, rules, fixture=True, now=now, disk=False)
        verdict = summarise(F, STRUCTURAL_IDS)
        expected = diag.get("expected")
        rows.append({"fixture": p.name, "fixture_id": diag.get("fixture_id"), "expected": expected,
                     "got": verdict, "match": verdict == expected,
                     "failed_checks": [f["id"] for f in F if f["verdict"] == "fail"]})
    negs = [r for r in rows if r["expected"] == "fail"]
    poss = [r for r in rows if r["expected"] == "pass"]
    controls = {
        "always_accept_control": {"negatives": len(negs),
                                  "would_accept": [r["fixture"] for r in negs if r["got"] == "pass"],
                                  "passed": len(negs) > 0 and all(r["got"] == "fail" for r in negs)},
        "always_reject_control": {"positives": len(poss),
                                  "would_reject": [r["fixture"] for r in poss if r["got"] == "fail"],
                                  "passed": len(poss) > 0 and all(r["got"] == "pass" for r in poss)},
    }
    mismatched = [r["fixture"] for r in rows if not r["match"]]
    okv = (not mismatched and all(c["passed"] for c in controls.values()) and len(rows) >= 8)
    return {"fixtures_dir": str(FIXTURES.relative_to(ROOT)), "count": len(rows),
            "negatives": len(negs), "positives": len(poss), "mismatched": mismatched,
            "controls": controls, "verdict": "pass" if okv else "fail", "rows": rows,
            "note": "fixture mode exercises the structural invariants only; disk pins and hygiene "
                    "are not applicable to synthetic fixtures"}


def run_selftest(rules: dict) -> dict:
    now = datetime.now(CST)
    raw = AGG.read_text()
    doc, meta = load_tracked(raw)
    base = check_aggregator(doc, raw, meta, rules, fixture=False, now=now, disk=True)
    base_struct = summarise(base, STRUCTURAL_IDS)
    cases = []

    def mutant(name, text, expect_id):
        d, m = load_tracked(text)
        F = check_aggregator(d, text, m, rules, fixture=False, now=now, disk=False)
        fired = [f["id"] for f in F if f["verdict"] == "fail"]
        cases.append({"mutant": name, "expected_invariant": expect_id, "fired": fired,
                      "caught": expect_id in fired})

    mutant("M1-join-class-ids",
           raw + '\nnote_merged: "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"\n', "A4-class-id-join")
    mutant("M2-composite-regularity",
           raw + '\nnote_composite: "the aggregate covers C0 or C2 data"\n', "A5-composite-regularity")
    mutant("M3-unpinned-component",
           re.sub(r"(?m)^(\s*sha256:\s*)[0-9a-f]{64}", r'\1"zz"', raw, count=1), "A3-component-pins")
    mutant("M4-conclusion-object",
           raw + '\nconclusion:\n  statement: "shared conclusion"\n', "A6-no-conclusion-object")
    mutant("M5-duplicate-key",
           raw + '\nrevised_at: "2026-09-12T01:00:00+08:00"\n', "H1-duplicate-keys")
    mutant("M6-future-timestamp",
           raw + '\ngenerated_at: "2099-01-01T00:00:00+08:00"\n', "H2-future-timestamps")

    null_ok = base_struct == "pass"
    caught_all = all(c["caught"] for c in cases)
    return {"measured_at": now.replace(microsecond=0).isoformat(),
            "null_control": {"live_index_structural_verdict": base_struct,
                             "structural_failures": [f["id"] for f in base if f["verdict"] == "fail"
                                                     and f["id"] in STRUCTURAL_IDS],
                             "passed": null_ok},
            "mutants": cases, "mutants_caught": f"{sum(c['caught'] for c in cases)}/{len(cases)}",
            "passed": bool(null_ok and caught_all)}


# ----------------------------------------------------------------------------- report
def author_cross_check() -> dict:
    out = Path("/tmp/w005_author_lint_crosscheck.json")
    try:
        p = subprocess.run([sys.executable, str(AUTHOR_LINT), "--report", "--out", str(out)],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        rep = json.loads(out.read_text()) if out.exists() else {}
        return {"tool": str(AUTHOR_LINT.relative_to(ROOT)), "exit": p.returncode,
                "aggregator_verdict": rep.get("aggregator_verdict"),
                "component_verdict": rep.get("component_verdict"),
                "fixtures_verdict": (rep.get("fixtures") or {}).get("verdict"),
                "overall_verdict": rep.get("overall_verdict"),
                "aggregator_sha256": rep.get("aggregator_sha256")}
    except Exception as exc:
        return {"tool": str(AUTHOR_LINT.relative_to(ROOT)), "error": repr(exc)}


def build_report() -> dict:
    now = datetime.now(CST)
    rules = load_rules()
    raw = AGG.read_text()
    doc, meta = load_tracked(raw)
    aggF = check_aggregator(doc, raw, meta, rules, fixture=False, now=now, disk=True)
    compF, comp = check_components(doc, rules, now)
    fixtures = run_fixtures(rules, now)
    measured = {"schemas/af_scc_regularities.yaml": sha256_file(AGG)}
    for cid, p in COMPONENTS.items():
        measured[str(p.relative_to(ROOT))] = sha256_file(p)

    # H3 pin-annotation consistency: declared pin time vs pinned file mtime
    h3 = []
    pin_notes = re.findall(r"pinned from disk at (20\d{2}-\d{2}-\d{2}T\d{2}:\d{2})", raw)
    for cid, p in COMPONENTS.items():
        mtime = datetime.fromtimestamp(p.stat().st_mtime, CST)
        for note in pin_notes:
            t = parse_ts(note)
            if t and abs((mtime - t).total_seconds()) > 300:
                h3.append({"class_id": cid, "declared_pin_time": note,
                           "file_mtime": mtime.isoformat(timespec="seconds"),
                           "delta_s": int((mtime - t).total_seconds())})
    hygiene = {
        "aggregator": {"duplicate_keys": [f"{k} x{n}" for k, n in meta.get("dup_keys", [])],
                       "future_timestamps": [f["value"] for f in find_future_timestamps(raw, now)]},
        "components": comp["hygiene"],
        "pin_annotation": h3,
    }
    hyg_fail = bool(hygiene["aggregator"]["duplicate_keys"] or hygiene["aggregator"]["future_timestamps"]
                    or h3 or any(c["duplicate_keys"] or c["future_timestamps"] for c in comp["hygiene"]))
    structural = summarise(aggF, STRUCTURAL_IDS)
    comp_struct = summarise(compF)
    return {
        "task_id": "W005-F2-REBIND",
        "agent": "worker-005",
        "node_id": "F2",
        "class_ids": SCC_CLASSES,
        "gate": "G-FORM",
        "measured_at": now.replace(microsecond=0).isoformat(),
        "pins": measured,
        "aggregator_findings": aggF,
        "aggregator_structural_verdict": structural,
        "component_findings": compF,
        "component_structural_verdict": comp_struct,
        "component_canonical": comp["components"],
        "hygiene": hygiene,
        "hygiene_verdict": "fail" if hyg_fail else "pass",
        "fixtures": fixtures,
        "cross_check_author_lint": author_cross_check(),
        "separation_verdict": "pass" if structural == "pass" and comp_struct == "pass" and fixtures["verdict"] == "pass" else "fail",
        "rebind_verdict": ("separation_pass__hygiene_fail" if (structural == "pass" and comp_struct == "pass"
                           and fixtures["verdict"] == "pass" and hyg_fail)
                           else ("pass" if (structural == "pass" and comp_struct == "pass"
                                            and fixtures["verdict"] == "pass") else "fail")),
        "falsifier": ("Re-measure the pins in this report: if either component hash differs from its "
                      "aggregator pin, if the aggregator text contains a joined class-id or composite "
                      "regularity token, if a fixture labelled fail is accepted (or pass rejected), or "
                      "if the hygiene findings are absent from a repaired revision, the corresponding "
                      "verdict here is superseded or refuted. A repaired aggregator with deduplicated "
                      "and non-future timestamps falsifies the H1/H2 findings specifically."),
        "authority": ("worker measurement only; worker events cannot set status=done, "
                      "validation_status=passed, or a gate verdict"),
        "limitations": [
            "structural, lexical and evidence-hygiene checks only; no mathematical judgement",
            "the fixture corpus is the 10 planted leaks; escape rate beyond it is not established",
            "worker-06 rules are a derived hypothesis (rules_version w06-draft-3), consumed as input, not authority",
            "the author lint cross-check is an agreement datapoint, not an independent accept",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--fixtures", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    here = Path(__file__).resolve().parent
    rules = load_rules()
    now = datetime.now(CST)
    if a.selftest:
        res = run_selftest(rules)
        out = Path(a.out) if a.out else here / "selftest.json"
        out.write_text(json.dumps(res, indent=2) + "\n")
        print(json.dumps({k: res[k] for k in ("null_control", "mutants_caught", "passed")}, indent=2))
        return 0 if res["passed"] else 1
    if a.fixtures:
        res = run_fixtures(rules, now)
        out = Path(a.out) if a.out else here / "fixtures_run.json"
        out.write_text(json.dumps(res, indent=2) + "\n")
        print(json.dumps({k: res[k] for k in ("count", "negatives", "positives", "mismatched",
                                              "controls", "verdict")}, indent=2))
        return 0 if res["verdict"] == "pass" else 1
    if a.report:
        rep = build_report()
        out = Path(a.out) if a.out else here / "report.json"
        out.write_text(json.dumps(rep, indent=2) + "\n")
        print(f"wrote {out}")
        print(f"structural={rep['aggregator_structural_verdict']} components={rep['component_structural_verdict']} "
              f"fixtures={rep['fixtures']['verdict']} hygiene={rep['hygiene_verdict']} -> {rep['rebind_verdict']}")
        for f in rep["aggregator_findings"] + rep["component_findings"]:
            if f["verdict"] == "fail":
                print(f"  FAIL {f['id']}: {f['detail']}")
        return 0 if not rep["rebind_verdict"].startswith("fail") else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
