#!/usr/bin/env python3
"""W48-F1-CLOSURE-PREFLIGHT-01 — independent, pre-registered closure preflight for F1.

Scope (class-bound): class AF-WCC-VAC-GEN, node F1, gate G-FORM, acceptance source
`astra-life03-close-findings` items (a)-(d) plus the G-FORM hash/publication criteria.

This checker is deliberately standalone: stdlib + PyYAML only, no import of
`research_map/*`, `artifacts/formulation/tools/*`, or any other swarm gate. It can be
re-run unchanged on the post-closure revision:

    python3 check_f1_closure.py --schema <new schemas/af_wcc_vacuum.yaml> \
        --expect-sha256 <new hash> --controls --out report.json

Each check carries a falsifier; the mutation controls prove the checks can flip.

Exit codes: 0 accept, 1 revise, 2 inconclusive, 3 missing input, 4 pinned-hash mismatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
FROZEN_CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
CALL_RE = re.compile(r"(AF_\{I\+\}|[A-Za-z_][A-Za-z0-9_]*)\s*\(")
BINDER_RE = re.compile(r"\b(not\s+exists|forall|exists)\b")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$")
LOGIC_KEYWORDS = {"forall", "exists", "not", "and", "or", "implies", "iff", "in", "subset",
                  "intersect", "let", "with", "such", "that", "if", "then", "where"}


# --------------------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------------------
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_iso(text: str):
    if not isinstance(text, str):
        return None
    raw = text.strip().strip('"').strip("'")
    if not ISO_RE.match(raw):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def walk(obj, path=""):
    """Yield (dotted_path, value) for every node."""
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


def traverse(doc, dotted: str):
    """Resolve a dotted fragment; returns (True, value) or (False, None)."""
    cur = doc
    if not dotted:
        return False, None
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys (any depth)."""


def _strict_construct_mapping(loader, node, deep=False):
    keys = set()
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in keys:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key: {key!r}", key_node.start_mark)
        keys.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_construct_mapping)


# --------------------------------------------------------------------------------------
# context
# --------------------------------------------------------------------------------------
@dataclass
class Ctx:
    schema_path: Path
    raw: str
    doc: dict
    sha: str
    mtime: datetime
    now: datetime
    canonical_path: Path
    canonical_doc: dict
    canonical_sha: str
    supplement_path: Path
    supplement_doc: dict
    supplement_sha: str
    frozen_path: Path
    frozen: dict
    frozen_sha: str
    mirror_path: Path
    mirror: dict
    mirror_sha: str
    reviews_dir: Path

    def with_raw(self, raw: str, path: Path, doc: dict | None = None) -> "Ctx":
        d = doc if doc is not None else yaml.safe_load(raw)
        return Ctx(
            schema_path=path, raw=raw, doc=d, sha=sha256_bytes(raw.encode()),
            mtime=datetime.fromtimestamp(path.stat().st_mtime, CST), now=self.now,
            canonical_path=self.canonical_path, canonical_doc=self.canonical_doc,
            canonical_sha=self.canonical_sha, supplement_path=self.supplement_path,
            supplement_doc=self.supplement_doc, supplement_sha=self.supplement_sha,
            frozen_path=self.frozen_path, frozen=self.frozen, frozen_sha=self.frozen_sha,
            mirror_path=self.mirror_path, mirror=self.mirror, mirror_sha=self.mirror_sha,
            reviews_dir=self.reviews_dir,
        )


# --------------------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------------------
def check_c1_duplicate_keys(ctx: Ctx) -> dict:
    counts: dict[str, list[int]] = {}
    for i, line in enumerate(ctx.raw.splitlines(), 1):
        m = TOP_KEY_RE.match(line)
        if m:
            counts.setdefault(m.group(1), []).append(i)
    dups = {k: v for k, v in counts.items() if len(v) > 1}
    safe_err = None
    try:
        safe_val = yaml.safe_load(ctx.raw)
    except Exception as e:  # pragma: no cover - safe_load is lenient by design
        safe_val, safe_err = None, f"{type(e).__name__}: {e}"
    strict_err = None
    try:
        yaml.load(ctx.raw, Loader=StrictLoader)
    except Exception as e:
        strict_err = f"{type(e).__name__}: {str(e).splitlines()[0]}"
    effective = None
    if isinstance(safe_val, dict):
        effective = {"revision": safe_val.get("revision"), "revised_at": safe_val.get("revised_at")}
    parser_disagreement = strict_err is not None
    verdict = "FAIL" if (dups or parser_disagreement) else "PASS"
    return {
        "id": "C1",
        "title": "no duplicate top-level keys; parsers agree on effective values",
        "closure_item": "a",
        "blocking": True,
        "verdict": verdict,
        "detail": (
            f"duplicate top-level keys: { {k: v for k, v in dups.items()} }; "
            f"strict loader: {'raises -> ' + strict_err if strict_err else 'accepts'}; "
            f"yaml.safe_load last-wins effective values: {effective}"
        ),
        "evidence": [f"{ctx.schema_path}:{ln}" for lines in dups.values() for ln in lines],
        "falsifier": (
            "a re-freeze with unique top-level keys on which yaml.safe_load and a duplicate-rejecting "
            "loader agree; then the duplicate-key finding is falsified and this check flips PASS"
        ),
    }


def _collect_timestamps(ctx: Ctx):
    out = []
    for i, line in enumerate(ctx.raw.splitlines(), 1):
        m = TOP_KEY_RE.match(line)
        if m and m.group(1) in {"authored_at", "revised_at", "revised_at_unused", "written_at", "created_at"}:
            val = line.split(":", 1)[1].strip().strip('"').strip("'").split(" #")[0].strip()
            ts = parse_iso(val)
            if ts is not None:
                out.append((f"{m.group(1)}@{i}", ts, val))
    ok, checked_at = traverse(ctx.doc, "f0_binding.checked_at")
    if ok and isinstance(checked_at, str):
        ts = parse_iso(checked_at)
        if ts is not None:
            out.append(("f0_binding.checked_at", ts, checked_at))
    return out


def check_c2_timestamps(ctx: Ctx) -> dict:
    stamps = _collect_timestamps(ctx)
    future, ahead = [], []
    for label, ts, raw in stamps:
        if ts > ctx.now:
            future.append({"field": label, "value": raw})
        if ts > ctx.mtime + timedelta(seconds=120):
            ahead.append({"field": label, "value": raw})
    malformed = [label for label, _ts, raw in stamps if not ISO_RE.match(raw)]
    verdict = "FAIL" if (future or ahead or malformed) else "PASS"
    return {
        "id": "C2",
        "title": "machine-readable timestamps not future-dated relative to write/now",
        "closure_item": "a",
        "blocking": True,
        "verdict": verdict,
        "detail": (
            f"schema mtime={ctx.mtime.isoformat()}; now={ctx.now.isoformat()}; "
            f"future_of_now={future}; ahead_of_mtime={ahead}; malformed={malformed}"
        ),
        "evidence": [f"{ctx.schema_path}:{ln}" for ln, line in enumerate(ctx.raw.splitlines(), 1)
                     if TOP_KEY_RE.match(line) and TOP_KEY_RE.match(line).group(1) in
                     {"revised_at", "revised_at_unused"}],
        "falsifier": (
            "re-freeze stamping every machine-readable timestamp with the wall clock at write time "
            "(no value later than the file mtime); the future-dating finding is then falsified"
        ),
    }


def check_c3_pointer(ctx: Ctx) -> dict:
    ptr = ctx.doc.get("class_contract_pointer")
    path_part, _, frag = (ptr or "").partition("#")
    resolves_canon = traverse(ctx.canonical_doc, frag)[0] if frag else False
    resolves_supp = traverse(ctx.supplement_doc, frag)[0] if frag else False
    canon_alt = traverse(ctx.canonical_doc, f"classes.{ctx.doc.get('class_id')}")[0]
    prefix_canonical = path_part.startswith("research_map/")
    verdict = "PASS" if (resolves_canon and prefix_canonical) else "FAIL"
    line = next((i for i, l in enumerate(ctx.raw.splitlines(), 1) if l.startswith("class_contract_pointer:")), None)
    return {
        "id": "C3",
        "title": "class_contract_pointer resolves inside the declared canonical F0",
        "closure_item": "b",
        "blocking": True,
        "contested": True,
        "adjudication_dependency": (
            "FROZEN rev26 + f0_mirror_conflict.json argue canonical declared-F0 (classes/*) and the "
            "authoring class-contract supplement (class_contracts/*) are two different logical artifacts, "
            "so this pointer is intentional; the controller must record REC-1 (pairing exception) or REC-2 "
            "(bounded re-freeze) before this finding can be closed or waived."
        ),
        "verdict": verdict,
        "detail": (
            f"pointer={ptr!r}; resolves in canonical declared-F0={resolves_canon}; "
            f"resolves in authoring supplement={resolves_supp}; canonical alternative "
            f"classes.{ctx.doc.get('class_id')} resolves={canon_alt}; path prefix is canonical tree={prefix_canonical}"
        ),
        "evidence": ([f"{ctx.schema_path}:{line}"] if line else []) + [
            f"{ctx.canonical_path}#{frag} (resolves={resolves_canon})",
            f"{ctx.supplement_path}#{frag} (resolves={resolves_supp})",
            f"{ctx.frozen_path}#f0_mirror_adjudication_request",
        ],
        "falsifier": (
            "either (i) the pointer is repointed to a fragment that resolves in the declared canonical F0 "
            "at a frozen hash, or (ii) the controller records the REC-1 pairing exception naming this "
            "pointer/tree pair; either disposition falsifies the 'unresolved pointer' reading"
        ),
    }


def check_c4_publication(ctx: Ctx) -> dict:
    frozen_files = ctx.frozen.get("files", {}) if isinstance(ctx.frozen, dict) else {}
    f1_canon = frozen_files.get("schemas/af_wcc_vacuum.yaml", {}).get("sha256")
    f1_auth = frozen_files.get("artifacts/formulation/schemas/af_wcc_vacuum.yaml", {}).get("sha256")
    f0_canon = frozen_files.get("research_map/formulation_taxonomy.yaml", {}).get("sha256")
    f0_auth = frozen_files.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256")
    logical = ctx.frozen.get("logical_artifacts", {}) if isinstance(ctx.frozen, dict) else {}
    mirror_req = ctx.frozen.get("f0_mirror_adjudication_request", {}) if isinstance(ctx.frozen, dict) else {}
    f1_aligned = f1_canon == f1_auth == ctx.sha
    f0_byte_identical = ctx.canonical_sha == ctx.supplement_sha
    mirror_status = ctx.mirror.get("answer") if isinstance(ctx.mirror, dict) else None
    verdict = "PASS" if (f1_aligned and f0_byte_identical) else "UNRESOLVED"
    return {
        "id": "C4",
        "title": "publication state: F1 aligned canonical/authoring/FROZEN; F0 pair adjudicated",
        "closure_item": "publication",
        "blocking": True,
        "verdict": verdict,
        "detail": (
            f"F1 canonical/authoring/FROZEN aligned={f1_aligned} "
            f"(canon={f1_canon[:12] if f1_canon else None}, auth={f1_auth[:12] if f1_auth else None}, measured={ctx.sha[:12]}); "
            f"F0 canonical={ctx.canonical_sha[:12]} vs authoring={ctx.supplement_sha[:12]} "
            f"byte-identical={f0_byte_identical} (frozen canon={str(f0_canon)[:12]}, auth={str(f0_auth)[:12]}); "
            f"mirror adjudication status={mirror_req.get('status')!r}; evidence answer={mirror_status!r}"
        ),
        "evidence": [str(ctx.frozen_path), str(ctx.mirror_path),
                     f"{ctx.frozen_path}#logical_artifacts"],
        "falsifier": (
            "a FROZEN revision that maps one logical F0 artifact to one hash in both trees (REC-2), or a "
            "recorded controller REC-1 exception declaring the pair intentional; until then the gate's "
            "'canonical == authoring' criterion is unsatisfiable and the verdict stays UNRESOLVED"
        ),
    }


def _defined_symbols(doc: dict) -> set:
    defined = set()
    for path, value in walk(doc):
        leaf = path.rsplit(".", 1)[-1]
        if path:
            defined.add(leaf)
            defined.add(leaf.replace("_", ""))
        if leaf in {"predicate_name", "symbol", "symbol_name", "name"} and isinstance(value, str):
            defined.add(value)
            defined.add(value.replace("_", ""))
    symbols = doc.get("symbol_definitions")
    if isinstance(symbols, dict):
        for k in symbols:
            defined.add(k)
            defined.add(k.replace("_", ""))
            defined.add(k.replace("{", "").replace("}", ""))
    return defined


def check_c5_symbols(ctx: Ctx) -> dict:
    formal = traverse(ctx.doc, "conclusion.statement_formal")[1]
    formal = formal if isinstance(formal, str) else ""
    tokens = sorted(set(CALL_RE.findall(formal)) - LOGIC_KEYWORDS)
    defined = _defined_symbols(ctx.doc)
    undefined, prose_only = [], []
    all_strings = [v for _p, v in walk(ctx.doc) if isinstance(v, str)]
    for tok in tokens:
        variants = {tok, tok.replace("_", ""), tok.replace("{", "").replace("}", "")}
        if variants & defined:
            continue
        undefined.append(tok)
        if any(tok.replace("{", "").replace("}", "") in s for s in all_strings):
            prose_only.append(tok)
    line = next((i for i, l in enumerate(ctx.raw.splitlines(), 1)
                 if l.strip().startswith("statement_formal:")), None)
    verdict = "FAIL" if undefined else "PASS"
    return {
        "id": "C5",
        "title": "every predicate symbol used in conclusion.statement_formal has a machine-readable definition",
        "closure_item": "c",
        "blocking": True,
        "verdict": verdict,
        "detail": (
            f"call-style symbols in statement_formal={tokens}; undefined={undefined}; "
            f"mentioned only in prose={prose_only}"
        ),
        "evidence": ([f"{ctx.schema_path}:{line}"] if line else []) + [
            f"{ctx.canonical_path}#classes.{ctx.doc.get('class_id')}.conclusion.text"],
        "falsifier": (
            "add a machine-readable definition for each symbol (a `symbol_definitions` entry or a "
            "predicate_name binding) and the finding is falsified"
        ),
    }


def check_c6_quantifiers(ctx: Ctx) -> dict:
    q = ctx.doc.get("quantifiers", {})
    ordered = q.get("ordered", []) if isinstance(q, dict) else []
    formal = q.get("formal", "") if isinstance(q, dict) else ""
    domains = q.get("domains", {}) if isinstance(q, dict) else {}
    kinds = [o.get("kind") for o in ordered if isinstance(o, dict)]
    extracted = [re.sub(r"\s+", "_", m) for m in BINDER_RE.findall(formal)]
    order_ok = kinds == extracted
    missing_domains = sorted({o.get("domain_id") for o in ordered if isinstance(o, dict)} - set(domains))
    visibility_def = str(traverse(ctx.doc, "visibility.definition")[1] or "")
    canonical_text = str(traverse(ctx.canonical_doc, f"classes.{ctx.doc.get('class_id')}.conclusion.text")[1] or "")
    canonical_tail = ("TAIL" in canonical_text) or ("[t0,T)" in canonical_text)
    definition_tail = ("TAIL" in visibility_def) or ("[t0,T)" in visibility_def)
    formal_tail = ("[t0,T)" in formal) or ("tail" in formal.lower())
    whole_curve = bool(re.search(r"gamma\s*(?:subset|\\subset|⊂)\s*J\^\-\(q\)", formal))
    tail_mismatch = (canonical_tail or definition_tail) and not formal_tail
    verdict = "FAIL" if (not order_ok or missing_domains or tail_mismatch or whole_curve) else "PASS"
    fline = next((i for i, l in enumerate(ctx.raw.splitlines(), 1) if l.strip().startswith("formal:")), None)
    return {
        "id": "C6",
        "title": "quantifier expansion agrees with ordered binders, domains, and the canonical tail predicate",
        "closure_item": "d",
        "blocking": True,
        "verdict": verdict,
        "detail": (
            f"ordered kinds={kinds}; extracted from quantifiers.formal={extracted}; order_ok={order_ok}; "
            f"domains missing={missing_domains}; canonical F0 declares tail predicate={canonical_tail}; "
            f"visibility.definition declares tail={definition_tail}; quantifiers.formal carries tail={formal_tail}; "
            f"quantifiers.formal uses whole-curve single-q containment={whole_curve}"
        ),
        "evidence": ([f"{ctx.schema_path}:{fline}"] if fline else []) + [
            f"{ctx.schema_path}#quantifiers.ordered",
            f"{ctx.schema_path}#visibility.definition",
            f"{ctx.canonical_path}#classes.{ctx.doc.get('class_id')}.conclusion.text",
        ],
        "falsifier": (
            "rewrite quantifiers.formal (and its negation) to the single-q TAIL predicate that the canonical "
            "F0 and visibility.definition declare; the contradiction is then falsified"
        ),
    }


def check_c7_f0_binding(ctx: Ctx) -> dict:
    declared = traverse(ctx.doc, "f0_binding.declared_f0_sha256")[1]
    declared_artifact = traverse(ctx.doc, "f0_binding.declared_f0_artifact")[1]
    ok = declared == ctx.canonical_sha
    verdict = "PASS" if ok else "FAIL"
    return {
        "id": "C7",
        "title": "f0_binding.declared_f0_sha256 equals measured canonical F0 hash",
        "closure_item": "binding",
        "blocking": False,
        "verdict": verdict,
        "detail": (
            f"declared={str(declared)[:16]} artifact={declared_artifact!r}; measured canonical="
            f"{ctx.canonical_sha[:16]} ({ctx.canonical_path}); match={ok}"
        ),
        "evidence": [f"{ctx.schema_path}#f0_binding", f"{ctx.canonical_path}"],
        "falsifier": "a re-freeze in which the declared hash is not the measured canonical F0 hash",
    }


def check_c8_class_binding(ctx: Ctx) -> dict:
    cid = ctx.doc.get("class_id")
    comps = ctx.doc.get("class_components", {})
    recomposed = "-".join(str(comps.get(k)) for k in ("asymptotics", "censorship", "matter", "genericity"))
    id_ok = (cid == recomposed) and (cid in FROZEN_CLASS_IDS)
    conclusion_type = traverse(ctx.doc, "conclusion.conclusion_type")[1]
    canon_type = traverse(ctx.canonical_doc, f"classes.{cid}.conclusion.type")[1]
    canon_axes_type = traverse(ctx.canonical_doc, f"classes.{cid}.axes.conclusion_type")[1]
    vocab_ok = conclusion_type == canon_type == canon_axes_type
    scc_hits = []
    for leaf in ("conclusion.statement_natural_language", "conclusion.statement_formal"):
        text = str(traverse(ctx.doc, leaf)[1] or "")
        if re.search(r"\bC[02]\b", text) or "inextendib" in text.lower():
            scc_hits.append(leaf)
    verdict = "PASS" if (id_ok and vocab_ok and not scc_hits) else "FAIL"
    return {
        "id": "C8",
        "title": "class identity and conclusion vocabulary bound to the canonical F0 class",
        "closure_item": "gate",
        "blocking": False,
        "verdict": verdict,
        "detail": (
            f"class_id={cid!r} recomposed={recomposed!r} in frozen set={cid in FROZEN_CLASS_IDS}; "
            f"conclusion_type={conclusion_type!r} canonical={canon_type!r} canonical_axes={canon_axes_type!r}; "
            f"SCC-token leakage in conclusion statements={scc_hits}"
        ),
        "evidence": [f"{ctx.schema_path}#conclusion", f"{ctx.canonical_path}#classes.{cid}"],
        "falsifier": "a class id or conclusion vocabulary that differs from the canonical F0 class object",
    }


def _hash_set(v) -> set:
    """Normalise a hash-valued field to a set of strings.

    rev12 corpus always used a scalar; the rev13 corpus adds dict-valued
    reviewed_sha256 maps (path -> hash) and list-valued variants. The original
    checker (b8fd03f8) crashed on those; this hardened copy flattens them.
    """
    out: set = set()
    if isinstance(v, str):
        out.add(v)
    elif isinstance(v, dict):
        for vv in v.values():
            out |= _hash_set(vv)
    elif isinstance(v, (list, tuple, set)):
        for vv in v:
            out |= _hash_set(vv)
    return out


def check_c9_review_status(ctx: Ctx) -> dict:
    listed = sorted(set(traverse(ctx.doc, "review_status.independent_reviewers")[1] or []))
    on_disk = {}
    if ctx.reviews_dir.is_dir():
        for f in sorted(ctx.reviews_dir.glob("*.json")):
            try:
                r = json.loads(f.read_text())
            except Exception:
                continue
            hashes: set = set()
            for key in ("artifact_sha256", "reviewed_sha256", "reviewed_snapshot_sha256"):
                hashes |= _hash_set(r.get(key))
            if ctx.sha in hashes and r.get("target_id") in (ctx.doc.get("node_id"), "F1", None):
                on_disk[r.get("reviewer") or f.stem] = r.get("verdict")
    missing = sorted(set(on_disk) - set(listed))
    verdict = "FAIL" if missing else "PASS"
    return {
        "id": "C9",
        "title": "review_status.independent_reviewers reflects hash-bound reviews on disk (advisory)",
        "closure_item": "metadata",
        "blocking": False,
        "verdict": verdict,
        "detail": (
            f"declared reviewers={listed}; hash-bound reviewers on disk at {ctx.sha[:12]}="
            f"{ {k: on_disk[k] for k in sorted(on_disk)} }; undeclared={missing}"
        ),
        "evidence": [f"{ctx.schema_path}#review_status", str(ctx.reviews_dir)],
        "falsifier": "update review_status.independent_reviewers so every hash-bound reviewer is listed",
    }


CHECKS = [check_c1_duplicate_keys, check_c2_timestamps, check_c3_pointer, check_c4_publication,
          check_c5_symbols, check_c6_quantifiers, check_c7_f0_binding, check_c8_class_binding,
          check_c9_review_status]


# --------------------------------------------------------------------------------------
# mutation controls (prove each blocking check can flip)
# --------------------------------------------------------------------------------------
def _mutate(ctx: Ctx, raw: str, tmp: Path, name: str) -> Ctx:
    p = tmp / name
    p.write_text(raw)
    return ctx.with_raw(raw, p)


def run_controls(ctx: Ctx, tmp: Path) -> list[dict]:
    results = []

    def record(cid, mutation, expected, ctx2):
        got = next(c["verdict"] for c in (fn(ctx2) for fn in CHECKS) if c["id"] == cid)
        results.append({
            "control": f"ctl-{cid}-{mutation}",
            "target_check": cid,
            "mutation": mutation,
            "expected": expected,
            "observed": got,
            "pass": got == expected,
        })

    # r1: de-duplicate top-level keys by dropping earlier duplicates (keep last-wins content)
    seen = {}
    lines = ctx.raw.splitlines()
    drop = set()
    for i, line in enumerate(lines, 1):
        m = TOP_KEY_RE.match(line)
        if m:
            if m.group(1) in seen:
                drop.add(seen[m.group(1)])
            seen[m.group(1)] = i
    r1 = "\n".join(l for i, l in enumerate(lines, 1) if i not in drop) + "\n"
    record("C1", "dedupe-top-level-keys", "PASS", _mutate(ctx, r1, tmp, "ctl_r1.yaml"))

    # r2: stamp all machine timestamps 5 minutes before now (also before temp-file mtime)
    past = (ctx.now - timedelta(minutes=5)).isoformat(timespec="seconds")
    r2 = re.sub(r'(revised_at(?:_unused)?:\s*)"[^"]+"', rf'\1"{past}"', ctx.raw)
    r2 = r2.replace('checked_at: "2026-09-12T00:30:00+08:00"', f'checked_at: "{past}"')
    record("C2", "stamp-timestamps-at-now-minus-5min", "PASS", _mutate(ctx, r2, tmp, "ctl_r2.yaml"))

    # r3: define the dangling symbols in a machine-readable block
    r3 = ctx.raw.rstrip() + ('\nsymbol_definitions:\n  AF_{I+}: "future null infinity of the MGHD"\n'
                             '  complete: "every null geodesic generator of I+ is future-complete"\n')
    record("C5", "add-symbol_definitions", "PASS", _mutate(ctx, r3, tmp, "ctl_r3.yaml"))

    # r4: rewrite the formal containment to the canonical tail predicate
    r4 = ctx.raw.replace("gamma subset J^-(q) intersect M",
                         "gamma([t0,T)) subset J^-(q) intersect M for some t0 in [0,T)")
    record("C6", "tail-form-containments", "PASS", _mutate(ctx, r4, tmp, "ctl_r4.yaml"))

    # r5: repoint the class contract at a fragment that resolves in the canonical F0
    r5 = ctx.raw.replace("artifacts/formulation/formulation_taxonomy.yaml#class_contracts.",
                         "research_map/formulation_taxonomy.yaml#classes.")
    record("C3", "canonical-pointer-fragment", "PASS", _mutate(ctx, r5, tmp, "ctl_r5.yaml"))

    # m1: corrupt the declared F0 hash (proves C7 is not vacuous)
    r6 = re.sub(r'(declared_f0_sha256:\s*")[0-9a-f]{8}', r"\1deadbeef", ctx.raw)
    record("C7", "corrupt-declared-f0-hash", "FAIL", _mutate(ctx, r6, tmp, "ctl_m1.yaml"))

    return results


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def build_ctx(args) -> Ctx:
    schema = Path(args.schema).resolve()
    canonical = Path(args.canonical_f0).resolve()
    supplement = Path(args.supplement_f0).resolve()
    frozen_p = Path(args.frozen).resolve()
    mirror_p = Path(args.mirror_evidence).resolve()
    raw = schema.read_text()
    now = parse_iso(args.now) if args.now else datetime.now(CST)
    return Ctx(
        schema_path=schema, raw=raw, doc=yaml.safe_load(raw), sha=sha256_bytes(raw.encode()),
        mtime=datetime.fromtimestamp(schema.stat().st_mtime, CST), now=now,
        canonical_path=canonical, canonical_doc=load_yaml(canonical), canonical_sha=sha256_file(canonical),
        supplement_path=supplement, supplement_doc=load_yaml(supplement), supplement_sha=sha256_file(supplement),
        frozen_path=frozen_p, frozen=load_yaml(frozen_p), frozen_sha=sha256_file(frozen_p),
        mirror_path=mirror_p, mirror=load_yaml(mirror_p), mirror_sha=sha256_file(mirror_p),
        reviews_dir=Path(args.reviews_dir).resolve(),
    )


def verify_snapshot(ctx: Ctx, snapdir: Path) -> list[dict]:
    expected = {
        f"af_wcc_vacuum.{ctx.sha[:8]}.yaml": ctx.sha,
        f"canonical_f0.{ctx.canonical_sha[:8]}.yaml": ctx.canonical_sha,
        f"supplement_f0.{ctx.supplement_sha[:8]}.yaml": ctx.supplement_sha,
        f"FROZEN.{ctx.frozen_sha[:8]}.json": ctx.frozen_sha,
        f"f0_mirror_conflict.{ctx.mirror_sha[:8]}.json": ctx.mirror_sha,
    }
    out = []
    for name, want in expected.items():
        p = snapdir / name
        got = sha256_file(p) if p.is_file() else None
        out.append({"snapshot": str(p), "expected_sha256": want, "observed_sha256": got, "match": got == want})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    root = Path(__file__).resolve().parents[3]
    ap.add_argument("--schema", default=str(root / "schemas/af_wcc_vacuum.yaml"))
    ap.add_argument("--expect-sha256", default=None)
    ap.add_argument("--canonical-f0", default=str(root / "research_map/formulation_taxonomy.yaml"))
    ap.add_argument("--supplement-f0", default=str(root / "artifacts/formulation/formulation_taxonomy.yaml"))
    ap.add_argument("--frozen", default=str(root / "artifacts/formulation/FROZEN.json"))
    ap.add_argument("--mirror-evidence", default=str(root / "artifacts/formulation/evidence/f0_mirror_conflict.json"))
    ap.add_argument("--reviews-dir", default=str(root / "reviews"))
    ap.add_argument("--now", default=None, help="ISO-8601 wall clock to use instead of the current time")
    ap.add_argument("--controls", action="store_true", help="run mutation controls")
    ap.add_argument("--snapshot-dir", default=None, help="verify pinned copies against measured hashes")
    ap.add_argument("--out", default=None, help="write report JSON here")
    args = ap.parse_args(argv)

    for p in (args.schema, args.canonical_f0, args.supplement_f0, args.frozen, args.mirror_evidence):
        if not Path(p).is_file():
            print(f"missing input: {p}", file=sys.stderr)
            return 3
    ctx = build_ctx(args)
    if args.expect_sha256 and ctx.sha != args.expect_sha256:
        print(f"pinned-hash mismatch: measured {ctx.sha}, expected {args.expect_sha256}", file=sys.stderr)
        return 4

    checks = [fn(ctx) for fn in CHECKS]
    controls = []
    if args.controls:
        with tempfile.TemporaryDirectory(prefix="w48_ctl_") as td:
            controls = run_controls(ctx, Path(td))

    blocking_fail = [c for c in checks if c["blocking"] and c["verdict"] == "FAIL"]
    blocking_unres = [c for c in checks if c["blocking"] and c["verdict"] == "UNRESOLVED"]
    verdict = "revise" if blocking_fail else ("inconclusive" if blocking_unres else "accept")
    report = {
        "schema_version": "1.0",
        "artifact_kind": "closure_preflight",
        "task_id": "W48-F1-CLOSURE-PREFLIGHT-01",
        "worker": "worker-048",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gate": "G-FORM",
        "acceptance_source": "research_map/events.jsonl#astra-life03-close-findings",
        "created_at": ctx.now.isoformat(timespec="seconds"),
        "inputs": {
            "schema": {"path": str(ctx.schema_path), "sha256": ctx.sha, "bytes": len(ctx.raw.encode()),
                       "mtime": ctx.mtime.isoformat()},
            "canonical_f0": {"path": str(ctx.canonical_path), "sha256": ctx.canonical_sha},
            "supplement_f0": {"path": str(ctx.supplement_path), "sha256": ctx.supplement_sha},
            "frozen": {"path": str(ctx.frozen_path), "sha256": ctx.frozen_sha},
            "mirror_evidence": {"path": str(ctx.mirror_path), "sha256": ctx.mirror_sha},
            "reviews_dir": str(ctx.reviews_dir),
        },
        "snapshot_verification": verify_snapshot(ctx, Path(args.snapshot_dir).resolve()) if args.snapshot_dir else [],
        "verdict": verdict,
        "checks": checks,
        "controls": controls,
        "controls_all_pass": all(c["pass"] for c in controls) if controls else None,
        "hard_failures": [f"{c['id']}: {c['title']}" for c in blocking_fail],
        "unresolved": [f"{c['id']}: {c['title']}" for c in blocking_unres],
        "rerun": (
            "python3 check_f1_closure.py --schema <post-closure schemas/af_wcc_vacuum.yaml> "
            "--expect-sha256 <post-closure hash> --now <wall clock> --controls --out report.postclosure.json"
        ),
        "checker_sha256": sha256_file(Path(__file__).resolve()),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(json.dumps({k: report[k] for k in ("task_id", "verdict", "hard_failures", "unresolved",
                                             "controls_all_pass")}, indent=2))
    if controls and not report["controls_all_pass"]:
        return 5
    return {"accept": 0, "revise": 1, "inconclusive": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
