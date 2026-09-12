"""Audit metrics library for the cosmic-censorship swarm.

Implements the enforcement layer for A0 (artifacts/audit/evaluation_rubric.yaml):
class binding, citation support, hard failures, duplication / effective sample size,
and information gain. Stdlib only (plus PyYAML for the rubric).

The library is deliberately fail-closed: unknown class IDs, missing falsifiers, missing
locators and missing artifacts are violations, not warnings.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
RUBRIC = ROOT / "artifacts" / "audit" / "evaluation_rubric.yaml"

CONCLUSION_TYPES = {
    "theorem", "conditional_theorem", "stability_result", "counterexample",
    "numerical_evidence", "formal_model", "open_problem",
}
CITATION_STATUS_WEIGHTS = {
    "verified_primary": 1.0,
    "verified_secondary": 0.5,
    "partial": 0.25,
    "unresolved": 0.0,
    "contradicted": -1.0,
}
CLASS_STATUSES = ("open_conjecture", "conditional", "refuted_candidate", "refuted", "settled_theorem")


# ---------------------------------------------------------------------------------------
# rubric loading
# ---------------------------------------------------------------------------------------
def load_rubric(path: str | Path = RUBRIC) -> dict[str, Any]:
    import yaml
    with open(path) as f:
        return yaml.safe_load(f)


def frozen_classes(rubric: dict[str, Any]) -> dict[str, dict]:
    return {c["id"]: c for c in rubric["frozen_classes"]}


# ---------------------------------------------------------------------------------------
# violations
# ---------------------------------------------------------------------------------------
@dataclass
class Violation:
    hf: str
    severity: str
    where: str
    detail: str
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"hf": self.hf, "severity": self.severity, "where": self.where,
                "detail": self.detail, "evidence": self.evidence}


def sha256_file(path: str | Path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------
# map integrity
# ---------------------------------------------------------------------------------------
def check_map_integrity(map_path: str | Path, root: str | Path = ROOT) -> list[Violation]:
    """HF-05: done/passed nodes must have an existing artifact with a recorded hash."""
    root = Path(root)
    m = json.loads(Path(map_path).read_text())
    out: list[Violation] = []
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            status = n.get("status")
            exists = bool(art) and (root / art).exists()
            if status == "done" and not exists:
                out.append(Violation(
                    "HF-05", "critical", f"{g['id']}/{n['id']}",
                    f"done node declares artifact {art!r} which does not exist",
                    {"artifact": art, "validation_status": n.get("validation_status")}))
            if status == "done" and exists and not n.get("sha256"):
                out.append(Violation(
                    "HF-05", "major", f"{g['id']}/{n['id']}",
                    f"done node artifact {art!r} has no recorded sha256",
                    {"artifact": art}))
            if status == "done" and not n.get("falsifier"):
                out.append(Violation(
                    "HF-06", "major", f"{g['id']}/{n['id']}",
                    "done node has no falsifier field", {}))
            if status == "done" and n.get("validation_status") not in {"passed"}:
                out.append(Violation(
                    "HF-05", "critical", f"{g['id']}/{n['id']}",
                    f"done node without passed validation_status ({n.get('validation_status')!r})", {}))
    # budget accounting: spent must not exceed budget
    for g in m.get("groups", []):
        if g.get("spent_agent_hours", 0) > g.get("budget_agent_hours", 0):
            out.append(Violation("HF-11", "major", g["id"], "spent exceeds budget", {}))
    return out


def artifact_inventory(map_path: str | Path, root: str | Path = ROOT) -> list[dict]:
    root = Path(root)
    m = json.loads(Path(map_path).read_text())
    inv = []
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            p = root / art if art else None
            inv.append({
                "group": g["id"], "node": n["id"], "status": n.get("status"),
                "artifact": art, "exists": bool(p and p.exists()),
                "is_dir": bool(p and p.is_dir()),
                "sha256": (sha256_file(p) if (p and p.is_file()) else None),
                "bytes": (p.stat().st_size if (p and p.is_file()) else None),
            })
    return inv


# ---------------------------------------------------------------------------------------
# class binding (HF-02 / HF-03 / HF-06)
# ---------------------------------------------------------------------------------------
def check_class_binding(claim: dict, classes: dict[str, dict]) -> list[Violation]:
    """Enforce one frozen class per claim, consistent conclusion type and evidence."""
    out: list[Violation] = []
    cid = claim.get("class_id")
    where = claim.get("claim_id") or claim.get("event_id") or claim.get("id") or "<claim>"
    if cid in ("GLOBAL", "DEFINITIONS"):
        # process/audit scope token: allowed only for statements that assert no mathematics,
        # except on audit/process nodes (A*) where the object is the harness itself
        node = str(claim.get("node_id", ""))
        if (claim.get("conclusion_type") in ("theorem", "conditional_theorem", "counterexample",
                                             "stability_result", "numerical_evidence")
                and not node.startswith("A")):
            out.append(Violation("HF-02", "critical", where,
                                 f"process-scope class token {cid!r} used with a mathematical "
                                 f"conclusion_type {claim.get('conclusion_type')!r}"))
        return out
    if cid not in classes:
        out.append(Violation("HF-02", "critical", where,
                             f"class_id {cid!r} is not in the frozen class registry"))
        return out
    cls = classes[cid]
    text = " ".join(str(claim.get(k, "")) for k in
                    ("statement", "assumptions", "conclusion", "conclusion_type", "notes"))
    _NEG = re.compile(r"(no|not|never|without|forbid|anti[_-]?scope|exclude|avoid|reject|"
                      r"must not|do not|does not|instead of|rather than)[^.;]{0,60}$", re.I)

    def _negated(pos: int) -> bool:
        return bool(_NEG.search(text[max(0, pos - 80):pos]))

    # disjunction of classes anywhere in the statement (ignoring explicit anti-scope/negations)
    meta_claim = bool(re.search(r"validator|checker|linter|harness|fixture|class[_-]separation|"
                                r"escape|false[ _]positive|audit_evidence", text, re.I))
    for other in classes:
        if other == cid:
            continue
        for m in re.finditer(re.escape(other), text):
            if not _negated(m.start()) and not meta_claim:
                out.append(Violation("HF-02", "critical", where,
                                     f"statement mentions a second frozen class {other}", {}))
                break
    for m in re.finditer(r"\bC\s*0\s*(?:or|/|,)\s*C\s*2\b|\bC\s*2\s*(?:or|/|,)\s*C\s*0\b",
                         text, re.I):
        if not _negated(m.start()) and not meta_claim:
            out.append(Violation("HF-02", "critical", where,
                                 "disjunctive C0/C2 formulation in one statement", {}))
            break
    ct = claim.get("conclusion_type")
    if ct not in CONCLUSION_TYPES:
        out.append(Violation("HF-02", "major", where, f"unknown conclusion_type {ct!r}", {}))
    elif ct == "theorem" and not claim.get("artifact_refs"):
        out.append(Violation("HF-01", "critical", where,
                             "theorem conclusion without artifact_refs", {}))
    if not claim.get("falsifier"):
        out.append(Violation("HF-06", "critical", where, "claim has no falsifier", {}))
    # evidence metadata leakage
    for ev in claim.get("evidence_refs", []) or []:
        if not isinstance(ev, dict):
            continue
        meta = ev.get("source_meta", ev)
        transfer = claim.get("transfer_argument")
        mism = []
        if "matter_model" in meta and meta["matter_model"] != cls.get("matter_model"):
            mism.append(f"matter_model={meta['matter_model']} vs class {cls.get('matter_model')}")
        if "cosmological_constant" in meta and meta["cosmological_constant"] != cls.get("cosmological_constant"):
            mism.append(f"Lambda={meta['cosmological_constant']} vs class {cls.get('cosmological_constant')}")
        if "dimension" in meta and meta["dimension"] != cls.get("dimension"):
            mism.append(f"dimension={meta['dimension']} vs class {cls.get('dimension')}")
        if "symmetry" in meta and meta["symmetry"] not in (cls.get("symmetry"), "none_required", None):
            mism.append(f"symmetry={meta['symmetry']} vs class {cls.get('symmetry')}")
        src_formulation = meta.get("formulation") or ev.get("formulation")
        if src_formulation == "SCC-C0" and cls.get("formulation") == "SCC-C2":
            mism.append("C0-inextendibility cited as C2 evidence (C0 is stronger; converse invalid)")
        if src_formulation == "SCC-C2" and cls.get("formulation") == "SCC-C0":
            mism.append("C2 result cited as C0 evidence without transfer_argument")
        if mism and not transfer:
            out.append(Violation("HF-02", "critical", where,
                                 "cross-class evidence without transfer_argument: " + "; ".join(mism),
                                 {"evidence": ev}))
        if mism and transfer:
            if ct == "theorem":
                out.append(Violation("HF-02", "critical", where,
                                     "cross-class evidence promoted to theorem", {}))
    # assumption smuggling: genericity/smallness asserted about the result must appear in assumptions
    assumptions = str(claim.get("assumptions", "")).lower()
    statement = str(claim.get("statement", "")).lower()
    asserts_generic = re.search(r"\bfor (?:all )?generic\b|\bgeneric(?:ally)? (?:initial )?data\b|"
                                r"\bgenerically\b|\boutside a (?:set of )?measure zero\b", statement)
    if asserts_generic and not _negated(asserts_generic.start()) and "generic" not in assumptions:
        out.append(Violation("HF-06", "major", where,
                             "statement asserts genericity of the result but assumptions do not define it", {}))
    small = re.search(r"\b(small|near|close to|perturbation of)\b", statement)
    if small and not _negated(small.start()) and \
       not re.search(r"\b(small|near|close|perturbation)\b", assumptions) and \
       claim.get("conclusion_type") in {"theorem", "conditional_theorem", "stability_result"}:
        out.append(Violation("HF-06", "major", where,
                             "statement uses a smallness/nearness hypothesis absent from assumptions", {}))
    if not assumptions.strip():
        out.append(Violation("HF-06", "major", where, "empty assumptions field", {}))
    return out


# ---------------------------------------------------------------------------------------
# citation support (HF-03)
# ---------------------------------------------------------------------------------------
def citation_support(citations: Iterable[dict]) -> dict:
    cits = list(citations)
    if not cits:
        return {"n": 0, "score": None, "unresolved": [], "contradicted": [], "no_locator": []}
    total = 0.0
    unresolved, contradicted, no_locator = [], [], []
    for c in cits:
        status = c.get("resolution_status", "unresolved")
        total += max(0.0, CITATION_STATUS_WEIGHTS.get(status, 0.0))
        if status in ("unresolved", "partial"):
            unresolved.append(c.get("cite_key") or c.get("title") or c.get("id"))
        if status == "contradicted":
            contradicted.append(c.get("cite_key") or c.get("title") or c.get("id"))
        if not (c.get("doi") or c.get("arxiv") or c.get("url") or c.get("journal_ref")):
            no_locator.append(c.get("cite_key") or c.get("title") or c.get("id"))
    return {
        "n": len(cits),
        "score": round(total / len(cits), 4),
        "unresolved": unresolved,
        "contradicted": contradicted,
        "no_locator": no_locator,
    }


def check_citations(claim: dict, registry: dict[str, dict]) -> list[Violation]:
    out: list[Violation] = []
    where = claim.get("claim_id") or claim.get("event_id") or "<claim>"
    for ref in claim.get("citation_refs", []) or []:
        key = ref if isinstance(ref, str) else ref.get("cite_key")
        entry = registry.get(key)
        if entry is None:
            out.append(Violation("HF-03", "critical", where, f"citation {key!r} not in ledger", {}))
            continue
        status = entry.get("resolution_status")
        if status in ("unresolved", "contradicted", "partial"):
            out.append(Violation("HF-03", "critical", where,
                                 f"citation {key!r} status={status}", {}))
        if not (entry.get("doi") or entry.get("arxiv") or entry.get("url")):
            out.append(Violation("HF-03", "major", where, f"citation {key!r} has no locator", {}))
    return out


# ---------------------------------------------------------------------------------------
# duplication / effective sample size
# ---------------------------------------------------------------------------------------
def _shingles(text: str, k: int = 5) -> set[str]:
    toks = re.findall(r"[a-z0-9]+", text.lower())
    if len(toks) < k:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def jaccard(a: str, b: str, k: int = 5) -> float:
    sa, sb = _shingles(a, k), _shingles(b, k)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def kish_ess(labels: Iterable[Any]) -> float:
    counts: dict[Any, int] = {}
    for x in labels:
        counts[x] = counts.get(x, 0) + 1
    n = sum(counts.values())
    if n == 0:
        return 0.0
    return (sum(counts.values()) ** 2) / sum(v * v for v in counts.values())


def duplication_report(texts: dict[str, str], threshold: float = 0.60) -> dict:
    ids = sorted(texts)
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            s = jaccard(texts[ids[i]], texts[ids[j]])
            if s >= threshold:
                pairs.append({"a": ids[i], "b": ids[j], "similarity": round(s, 4)})
    novelty = {}
    for i in ids:
        best = 0.0
        for j in ids:
            if i == j:
                continue
            best = max(best, jaccard(texts[i], texts[j]))
        novelty[i] = round(1.0 - best, 4)
    mean_novelty = sum(novelty.values()) / len(novelty) if novelty else None
    return {
        "n": len(ids),
        "threshold": threshold,
        "duplicate_pairs": pairs,
        "duplicate_cluster_rate": round(len(pairs) / max(1, len(ids)), 4),
        "mean_novelty": mean_novelty,
        "novelty": novelty,
    }


# ---------------------------------------------------------------------------------------
# information gain
# ---------------------------------------------------------------------------------------
def entropy_bits(counts: Iterable[float]) -> float:
    vals = [c for c in counts if c > 0]
    tot = sum(vals)
    if tot <= 0:
        return 0.0
    return -sum((v / tot) * math.log2(v / tot) for v in vals)


def class_state_entropy(state: dict[str, str]) -> float:
    """Entropy over unresolved-class states. settled/refuted classes carry less uncertainty."""
    weight = {"open_conjecture": 4.0, "conditional": 2.0, "refuted_candidate": 1.0,
              "refuted": 0.0, "settled_theorem": 0.0}
    return entropy_bits([weight.get(v, 1.0) for v in state.values()])


def information_gain(before: dict[str, str], after: dict[str, str]) -> float:
    return round(class_state_entropy(before) - class_state_entropy(after), 4)


def ig_per_cost(ig_bits: float, tokens: int | None, agent_hours: float | None) -> dict:
    return {
        "ig_bits": ig_bits,
        "ig_per_1k_tokens": (round(ig_bits / (tokens / 1000.0), 6) if tokens else None),
        "ig_per_agent_hour": (round(ig_bits / agent_hours, 6) if agent_hours else None),
    }


# ---------------------------------------------------------------------------------------
# reviewer agreement
# ---------------------------------------------------------------------------------------
def cohen_kappa(a: list, b: list) -> float | None:
    if len(a) != len(b) or not a:
        return None
    n = len(a)
    labels = sorted(set(a) | set(b))
    agree = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    if pe >= 1.0:
        return 1.0
    return round((agree - pe) / (1 - pe), 4)


# ---------------------------------------------------------------------------------------
# seed hygiene (HF-09)
# ---------------------------------------------------------------------------------------
def check_seed_hygiene(result: dict) -> list[Violation]:
    out: list[Violation] = []
    where = result.get("result_id", "<result>")
    seeds = result.get("seeds")
    n_seeds = len(seeds) if isinstance(seeds, (list, tuple)) else result.get("n_seeds")
    if result.get("statistic") in ("max", "best") and (n_seeds or 0) < 8:
        out.append(Violation("HF-09", "major", where,
                             f"max/best statistic over {n_seeds} seeds (<8); report mean+/-sd", {}))
    if result.get("reported") == "best" and not result.get("mean"):
        out.append(Violation("HF-09", "major", where,
                             "best reported without mean/sd", {}))
    return out


def check_budget_match(arms: list[dict], tol: float = 0.02) -> list[Violation]:
    """HF-11: matched-budget arms must match total tokens and wall-clock within tol."""
    out: list[Violation] = []
    if not arms:
        return out
    for key in ("total_tokens", "wall_clock_s"):
        vals = [a.get(key) for a in arms]
        if any(v is None for v in vals):
            out.append(Violation("HF-11", "major", "ablation",
                                 f"arm budget field {key} missing in some arm", {}))
            continue
        lo, hi = min(vals), max(vals)
        if lo <= 0 or (hi - lo) / lo > tol:
            out.append(Violation("HF-11", "critical", "ablation",
                                 f"{key} not matched within {tol:.0%}: {vals}", {}))
    return out


# ---------------------------------------------------------------------------------------
# cross-project contamination (HF-13)
# ---------------------------------------------------------------------------------------
BASE_PROJECT_TOKENS = [
    "cubic graph", "minimum degree", "min degree", "cap set", "cap-set",
    "funsearch", "eight-cycle", "8-cycle", "priority function",
    "weakly connected component", "strongly connected component",
]
BASE_PROJECT_PREFIXES = ("data/", "erdos64/", "framework/", "runs/", "repro/",
                         "HANDOFF.md", "README.md", "artifacts/audit/")


def check_contamination(text: str, where: str, path: str = "") -> list[Violation]:
    if any(path.startswith(p) for p in BASE_PROJECT_PREFIXES):
        return []
    out: list[Violation] = []
    for tok in BASE_PROJECT_TOKENS:
        for m in re.finditer(r"\b" + re.escape(tok), text, re.I):
            ctx = text[max(0, m.start() - 200):m.start() + 200]
            # explicit anti-scope, disambiguation, or guard-list contexts are not contamination
            if re.search(r"(not|never|must not|forbid|contaminat|anti[_-]?scope|exclude|"
                         r"disambiguat|do not read|is not|are not|reads? it as|misread|"
                         r"rather than|instead of|cross[_-]?domain|regex)", ctx, re.I):
                continue
            out.append(Violation("HF-13", "minor", where,
                                 f"base-project token {tok!r} inside a cosmic-censorship artifact",
                                 {"path": path}))
            break
    return out


# ---------------------------------------------------------------------------------------
# ledger scope metadata (G-LIT)
# ---------------------------------------------------------------------------------------
SCOPE_KEYS = ("matter_model", "cosmological_constant", "dimension", "symmetry")


def check_self_certification(records: list[dict]) -> list[Violation]:
    """HF-14: no self-assigned 'accepted'/'passed'/'supports_claim' without a reviewer verdict."""
    out: list[Violation] = []
    for r in records:
        where = r.get("theorem_id") or r.get("claim_id") or r.get("event_id") or "<record>"
        accepted = (str(r.get("status", "")).lower() in ("accepted", "passed")
                    or r.get("supports_claim") is True
                    or str(r.get("validation_status", "")).lower() == "passed")
        has_review = bool(r.get("reviewer_verdicts") or r.get("review_verdict")
                          or r.get("reviewed_by"))
        if accepted and not has_review:
            out.append(Violation("HF-14", "critical", f"ledger/{where}",
                                 "self-certified acceptance: status/supports_claim set with no "
                                 "independent reviewer verdict", {"source": r.get("_source", "")}))
    return out


def check_ledger_scope(citations: list[dict]) -> list[Violation]:
    """Every ledger entry must record the source's physical scope so claims can be
    checked for class leakage (matter model, Lambda, dimension, symmetry, formulation).
    Aggregated per ledger file to keep the report readable."""
    missing_by_file: dict[str, list[str]] = {}
    for c in citations:
        key = c.get("cite_key") or c.get("source_id") or c.get("title")
        meta = c.get("source_meta", {})
        missing = [k for k in SCOPE_KEYS if k not in meta]
        if not meta.get("formulation") and not c.get("formulation"):
            missing.append("formulation")
        if missing:
            src = c.get("_source", "ledger")
            missing_by_file.setdefault(src, []).append(f"{key}({','.join(missing)})")
    out: list[Violation] = []
    for src, entries in sorted(missing_by_file.items()):
        out.append(Violation("HF-03", "major", f"ledger:{src}",
                             f"{len(entries)} of the ledger's citations lack class-scope metadata "
                             f"(matter_model/Lambda/dimension/symmetry/formulation); "
                             f"first: {', '.join(entries[:4])}",
                             {"file": src}))
    return out


# ---------------------------------------------------------------------------------------
# report helpers
# ---------------------------------------------------------------------------------------
def summarize(violations: list[Violation]) -> dict:
    by_hf: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for v in violations:
        by_hf[v.hf] = by_hf.get(v.hf, 0) + 1
        by_sev[v.severity] = by_sev.get(v.severity, 0) + 1
    return {"total": len(violations), "by_hf": by_hf, "by_severity": by_sev,
            "critical": by_sev.get("critical", 0)}


def write_json(path: str | Path, obj: Any) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, sort_keys=True)
    p.write_text(text + "\n")
    return sha256_text(text)
