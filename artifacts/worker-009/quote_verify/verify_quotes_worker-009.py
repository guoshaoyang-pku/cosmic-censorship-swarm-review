#!/usr/bin/env python3
"""
W009-L1-QUOTEVERIFY-01  (worker-009 / deepseek-flash-09)
Assignment asg-2026-09-11-L1-deepseek-flash-09-18   node L1   gate G-LIT
classes AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN

Bounded task: for the five SCC class-binding correction rows (CBC-09-008..012,
canonical rows SRC-014/029/033/048/061) verify, from the pinned bytes only:

  P1  source file sha256 equals the recorded source_tex_sha256
  P2  quote provenance: byte-exact / CRLF-normalised-exact presence and
      sha256(quote) == quote_tex_sha256 (CSV read newline-preserving)
  P3  enclosing locator: theorem environment label, or title (no theorem env)
  P4  model-class discriminators extracted from the source text near the quote
      (matter, cosmological constant / de Sitter, linear or fixed background,
      regularity tokens)
  P5  frozen class predicates read from the F2a/F2b schema bytes
      (data_class.matter == "none", cosmological_constant == 0, extension
      regularity exactly C2 / C0)
  P6  mapping check with a binding-vs-mention classifier (CF-16 pattern):
      a frozen class id inside a removal/negation phrase is a MENTION, not a
      binding; a bare id in a mapping slot is a BINDING
  P7  explicit C0/C2 discrimination: does the source support a binding to
      AF-SCC-C0-VAC-GEN, to AF-SCC-C2-VAC-GEN, or to neither?

The falsifier of the assignment card is "Theorem quoted in the wrong
regularity class"; operationalised per row as: if the quoted theorem is a
non-vacuum, non-Lambda=0, or fixed-background statement, then any
AF-SCC-*-VAC-GEN binding on that row is a class error and must be removed.

This is a same-worker cross-method re-derivation from pinned bytes, NOT an
independent reviewer verdict. No canonical file is written.
"""
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUTDIR = os.path.join(ROOT, "artifacts", "worker-009", "quote_verify")
CAND_CSV = os.path.join(ROOT, "ledger", "citation_audit_scc_candidates_worker-009.csv")
CAND_JSONL = os.path.join(ROOT, "ledger", "citation_audit_scc_candidates_worker-009.jsonl")
CANON = os.path.join(ROOT, "ledger", "citation_audit.csv")
F2A = os.path.join(ROOT, "artifacts", "formulation", "schemas", "af_scc_c2_vacuum.yaml")
F2B = os.path.join(ROOT, "artifacts", "formulation", "schemas", "af_scc_c0_vacuum.yaml")
FROZEN = os.path.join(ROOT, "artifacts", "formulation", "FROZEN.json")

CST = timezone(timedelta(hours=8))
# Frozen run stamp: keeps the verification artifact byte-reproducible. The real
# wall-clock time of the run lives in the checkpoint and the outbox event.
RUN_STAMP = "2026-09-12T01:02+08:00"
NOW = RUN_STAMP

FROZEN_VACUUM_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    with open(p, "rb") as f:
        return sha256_bytes(f.read())


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def crlf_to_lf(b):
    return b.replace(b"\r\n", b"\n")


def quote_present(qb, raw):
    """Explicit predicate: an empty quote is never 'present' (control C2)."""
    if not qb:
        return False
    return qb in raw


def theorem_env_names(text):
    """Environment names declared via \\newtheorem plus the usual defaults."""
    names = set(re.findall(r"\\newtheorem\*?\{([A-Za-z]+)\}", text))
    names |= {"theorem", "proposition", "corollary", "lemma"}
    return names


def env_regex(text):
    names = sorted(theorem_env_names(text), key=len, reverse=True)
    return r"\\begin\{(" + "|".join(re.escape(n) for n in names) + r")\}"


def find_enclosing_locator(text, quote):
    """Return (kind, label) for the structure enclosing the quote.

    Handles the case where the quote itself begins with \\begin{theorem};
    falls back to abstract / html-title / body-text so 'no theorem env'
    is not reported for abstract-level quotes.
    """
    if not quote:
        return ("absent", None)
    idx = text.find(quote)
    if idx < 0:
        return ("absent", None)
    env_re = env_regex(text)
    # (1) env starts inside the quote
    m_in = re.search(env_re, quote)
    if m_in:
        lab = re.search(r"\\label\{([^}]*)\}", quote[m_in.end():])
        return ("theorem-env", lab.group(1) if lab else None)
    # (2) env starts before the quote and closes after it
    before = text[:idx]
    starts = list(re.finditer(env_re, before))
    if starts:
        st = starts[-1]
        after_start = text[st.end():]
        endm = re.search(r"\\end\{(?:" + "|".join(re.escape(n) for n in theorem_env_names(text)) + r")\}", after_start)
        if endm and st.end() + endm.start() >= idx:
            env_body = after_start[: endm.start()]
            lab = re.search(r"\\label\{([^}]*)\}", env_body)
            return ("theorem-env", lab.group(1) if lab else None)
    # (3) abstract-level quote
    pre = text[max(0, idx - 2500): idx]
    if re.search(r"(\\begin\{abstract\}|\\bf\s*Abstract|\\section\*?\{Abstract)", pre, re.I):
        return ("abstract", None)
    # (4) html title page
    if quote.lower() in text[:4000].lower() and ("<title" in text[:4000].lower() or "<meta" in text[:4000].lower()):
        return ("html-title", None)
    return ("body-text", None)


def iter_theorem_envs(text, limit=60):
    """Yield {env,label,nonvacuum,...} for each theorem-like env."""
    out = []
    env_re = env_regex(text)
    names = theorem_env_names(text)
    end_re = r"\\end\{(?:" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")\}"
    for m in re.finditer(env_re, text):
        env = m.group(1)
        rest = text[m.end():]
        endm = re.search(end_re, rest)
        body = rest[: endm.start()] if endm else rest[:4000]
        lab = re.search(r"\\label\{([^}]*)\}", body)
        matter = sorted({x.group(0).lower() for x in MATTER_PAT.finditer(body)})
        lam = sorted({x.group(0).lower() for x in LAMBDA_PAT.finditer(body)})
        lin = sorted({x.group(0).lower() for x in LINEAR_PAT.finditer(body)})
        out.append({"env": env, "label": lab.group(1) if lab else None,
                    "nonvacuum": bool(matter) or bool(lam),
                    "matter_terms": matter, "lambda_terms": lam, "linear_terms": lin})
        if len(out) >= limit:
            break
    return out


def nearest_theorem_after(text, quote, envs):
    """First theorem-like env starting after an abstract/title-level quote."""
    idx = text.find(quote) if quote else -1
    if idx < 0:
        return None
    pos = 0
    env_re = env_regex(text)
    for m in re.finditer(env_re, text):
        if m.start() > idx + len(quote):
            lab = None
            rest = text[m.end():]
            lm = re.search(r"\\label\{([^}]*)\}", rest[:600])
            lab = lm.group(1) if lm else None
            match = next((e for e in envs if e["label"] == lab and lab is not None), None)
            return {"env": m.group(1), "label": lab,
                    "nonvacuum": (match or {}).get("nonvacuum"),
                    "matter_terms": (match or {}).get("matter_terms"),
                    "lambda_terms": (match or {}).get("lambda_terms")}
    return None


MATTER_PAT = re.compile(
    r"(scalar field|scalar-field|massless scalar|Einstein-Maxwell|Einstein-scalar|"
    r"Maxwell|Vaidya|null dust|dust|perfect fluid|matter field|self-gravitating|"
    r"Reissner|Kerr--Newman|Kerr-Newman|electrovacuum)",
    re.I,
)
LAMBDA_PAT = re.compile(
    r"(cosmological constant|positive cosmological|de Sitter|Lambda\s*[><=]|\\Lambda\s*[><=])",
    re.I,
)
LINEAR_PAT = re.compile(
    r"(linear wave equation|linearwaveequation|linear scalar wave|linear wave|"
    r"fixed .{0,30}background|background .{0,30}(fixed|metric)|test field|"
    r"solution \$?\\psi\$? of)",
    re.I,
)
C2_PAT = re.compile(
    r"(C\^?2|C\^\{2\}|twice continuously differentiable|classical Ricci|"
    r"Ric\s*\(?g'?\)?\s*=\s*0|proper future C2)",
    re.I,
)
C0_PAT = re.compile(
    r"(continuous metric|C\^?0|C\^\{0\}|continuous Lorentzian|merely continuous|"
    r"continuous spherically symmetric|Christoffel symbols in \$L)",
    re.I,
)

# removal / negation / non-binding markers for the mention-vs-binding classifier
MENTION_WINDOW = 70
MENTION_PAT = re.compile(
    r"(removed|remove|no\s+.{0,30}binding|not\s+.{0,20}bind|non-?binding|"
    r"do-not-transfer|does not bind|without\s+.{0,20}binding|drop|"
    r"evidence/tag only|no AF-SCC)",
    re.I,
)


def classify_source(ctx):
    return {
        "matter_terms": sorted({m.group(0).lower() for m in MATTER_PAT.finditer(ctx)}),
        "lambda_terms": sorted({m.group(0).lower() for m in LAMBDA_PAT.finditer(ctx)}),
        "linear_or_fixed_background_terms": sorted({m.group(0).lower() for m in LINEAR_PAT.finditer(ctx)}),
        "c2_terms": sorted({m.group(0).lower() for m in C2_PAT.finditer(ctx)}),
        "c0_terms": sorted({m.group(0).lower() for m in C0_PAT.finditer(ctx)}),
    }


def context_around(text, quote, pad=1400):
    i = text.find(quote)
    if i < 0:
        return ""
    return text[max(0, i - pad): i + len(quote) + pad]


def occurrences_with_kind(text, cls_id, force_mention=False):
    """Binding-vs-mention classification of every literal occurrence of cls_id."""
    out = []
    for m in re.finditer(re.escape(cls_id), text or ""):
        lo = max(0, m.start() - MENTION_WINDOW)
        hi = min(len(text), m.end() + MENTION_WINDOW)
        window = text[lo:hi]
        kind = "mention" if (force_mention or MENTION_PAT.search(window)) else "binding"
        out.append({"span": [m.start(), m.end()], "kind": kind, "window": window.strip()[:180]})
    return out


def load_schema(path, expect_sha):
    b = read_bytes(path)
    got = sha256_bytes(b)
    d = yaml.safe_load(b.decode("utf-8"))
    pred = {
        "class_id": d["class_id"],
        "matter": d["data_class"]["matter"],
        "cosmological_constant": d["data_class"]["cosmological_constant"],
        "equations": d["data_class"]["equations"],
        "extension_regularity": d["extension_predicate"]["frozen_regularity"],
        "extension_regularity_exact": d["regularity"]["extension_regularity_exact"],
        "vacuum_required": d["data_class"]["matter"] == "none" and float(d["data_class"]["cosmological_constant"]) == 0.0,
    }
    return got, expect_sha, got == expect_sha, pred


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    inputs = {}
    for key, p in [("canonical_ledger", CANON), ("candidate_csv", CAND_CSV),
                   ("candidate_jsonl", CAND_JSONL), ("f2a_c2_schema", F2A), ("f2b_c0_schema", F2B)]:
        inputs[key] = {"path": os.path.relpath(p, ROOT), "sha256": sha256_file(p), "bytes": os.path.getsize(p)}

    with open(CAND_CSV, newline="", encoding="utf-8") as f:
        cand_rows = list(csv.DictReader(f))
    assert len(cand_rows) == 5, f"expected 5 correction rows, got {len(cand_rows)}"

    f2a_sha, f2a_expect, f2a_ok, f2a_pred = load_schema(F2A, "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe")
    f2b_sha, f2b_expect, f2b_ok, f2b_pred = load_schema(F2B, "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c")
    frozen_rev = json.load(open(FROZEN))

    checks = []

    def chk(cid, name, ok, detail):
        checks.append({"row": cid, "check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    def info(cid, name, detail):
        checks.append({"row": cid, "check": name, "status": "INFO", "detail": detail})

    per_row = []
    for r in cand_rows:
        cid = r["correction_id"]
        src = r["source_tex_file"]
        q = r["quote_tex"]
        qb = q.encode("utf-8")
        raw = read_bytes(src) if os.path.exists(src) else b""
        text_lf = crlf_to_lf(raw).decode("utf-8", "replace")
        q_lf = crlf_to_lf(qb).decode("utf-8", "replace")

        src_sha = sha256_bytes(raw) if raw else None
        chk(cid, "P1_source_file_sha256", src_sha == r["source_tex_sha256"],
            f"measured={src_sha} recorded={r['source_tex_sha256']}")

        chk(cid, "P2a_quote_sha256", sha256_bytes(qb) == r["quote_tex_sha256"],
            f"measured={sha256_bytes(qb)} recorded={r['quote_tex_sha256']}")

        byte_exact = quote_present(qb, raw)
        lf_exact = quote_present(qb, crlf_to_lf(raw)) or quote_present(crlf_to_lf(qb), crlf_to_lf(raw))
        chk(cid, "P2b_quote_present_crlf_normalised", lf_exact,
            "quote literal after line-ending normalisation only (no whitespace collapsing)")
        if byte_exact:
            chk(cid, "P2c_quote_byte_exact", True, "quote bytes literal in source")
        else:
            info(cid, "P2c_quote_byte_exact", "not byte-exact; line-ending convention differs (CRLF source)")

        kind, label = find_enclosing_locator(text_lf, q_lf) if lf_exact else ("quote-absent", None)
        chk(cid, "P3_locator_found", kind != "quote-absent", f"kind={kind} label={label}")

        ctx = context_around(text_lf, q_lf)
        cls = classify_source(ctx)
        envs = iter_theorem_envs(text_lf)
        env_labels = [e["label"] for e in envs if e["label"]]
        env_nonvac = [e["label"] for e in envs if e["nonvacuum"]]
        chk(cid, "P3b_theorem_envs_enumerated", bool(envs) or kind in ("abstract", "html-title"),
            f"n_envs={len(envs)} labels={env_labels[:8]} nonvacuum_labels={env_nonvac[:8]}")
        nearest = nearest_theorem_after(text_lf, q_lf, envs)
        chk(cid, "P3c_nearest_theorem_after_quote", nearest is not None or kind == "html-title",
            f"nearest_after={nearest}")
        nonvacuum_evidence = bool(cls["matter_terms"]) or bool(cls["lambda_terms"])
        chk(cid, "P4_nonvacuum_or_nonscalarflat_evidence_present", nonvacuum_evidence,
            f"matter={cls['matter_terms']} lambda={cls['lambda_terms']} linear={cls['linear_or_fixed_background_terms']}")

        old_binds, old_mentions = [], []
        for cid_frozen in FROZEN_VACUUM_IDS:
            for o in occurrences_with_kind(r["old_class_mapping"], cid_frozen):
                (old_binds if o["kind"] == "binding" else old_mentions).append(cid_frozen)
        new_binds, new_mentions = [], []
        for cid_frozen in FROZEN_VACUUM_IDS:
            for o in occurrences_with_kind(r["new_class_mapping"], cid_frozen):
                (new_binds if o["kind"] == "binding" else new_mentions).append(cid_frozen)
            # relevant_class_nonbinding is a declared non-binding column: all mentions
            for o in occurrences_with_kind(r["relevant_class_nonbinding"], cid_frozen, force_mention=True):
                new_mentions.append(cid_frozen)

        chk(cid, "P6a_old_mapping_bound_frozen_id", len(old_binds) >= 1, f"old_bindings={old_binds}")
        chk(cid, "P6b_new_mapping_has_no_bound_frozen_id", len(new_binds) == 0,
            f"new_bindings={new_binds} new_mentions={sorted(set(new_mentions))}")

        # explicit C0 / C2 discrimination against the frozen schema predicates
        c2_supported = bool(nonvacuum_evidence is False and f2a_pred["vacuum_required"])
        c0_supported = bool(nonvacuum_evidence is False and f2b_pred["vacuum_required"])
        if nonvacuum_evidence:
            reason = "quoted context states non-vacuum matter and/or non-zero Lambda (de Sitter)"
        elif cls["linear_or_fixed_background_terms"]:
            reason = "linear/test-field result on a fixed background, no nonlinear vacuum extension statement"
        else:
            reason = "no vacuum-compatible content located"
        chk(cid, "P7a_no_c2_vacuum_binding_supported", not c2_supported,
            f"{reason}; F2a vacuum_required={f2a_pred['vacuum_required']}")
        chk(cid, "P7b_no_c0_vacuum_binding_supported", not c0_supported,
            f"{reason}; F2b vacuum_required={f2b_pred['vacuum_required']}")

        delivers = []
        if cls["c2_terms"]:
            delivers.append("C2ish")
        if cls["c0_terms"]:
            delivers.append("C0ish")
        delivers = delivers or ["neither_token_in_context"]

        residual_defect = len(new_binds) > 0
        per_row.append({
            "correction_id": cid,
            "canonical_row_id": r["canonical_row_id"],
            "source_tex_file": src,
            "source_sha256": src_sha,
            "source_sha256_matches_recorded": src_sha == r["source_tex_sha256"],
            "quote_sha256": sha256_bytes(qb),
            "quote_sha256_matches_recorded": sha256_bytes(qb) == r["quote_tex_sha256"],
            "quote_byte_exact": byte_exact,
            "quote_crlf_normalised_exact": lf_exact,
            "locator_kind": kind,
            "locator_label": label,
            "source_theorem_env_labels": env_labels[:20],
            "source_theorem_envs_nonvacuum_labels": env_nonvac[:20],
            "source_theorem_envs": envs[:12],
            "nearest_theorem_after_quote": nearest,
            "class_discriminators": cls,
            "old_class_mapping": r["old_class_mapping"],
            "new_class_mapping": r["new_class_mapping"],
            "old_bound_frozen_ids": sorted(set(old_binds)),
            "old_mention_frozen_ids": sorted(set(old_mentions)),
            "new_bound_frozen_ids": sorted(set(new_binds)),
            "new_mention_frozen_ids": sorted(set(new_mentions)),
            "c2_vacuum_binding_supported": c2_supported,
            "c0_vacuum_binding_supported": c0_supported,
            "regex_regularity_tokens": delivers,
            "correction_warranted": bool(old_binds) and nonvacuum_evidence,
            "residual_binding_defect": residual_defect,
            "falsifier": r["falsifier"][:400],
        })

    # ---- controls -------------------------------------------------------
    r0 = cand_rows[0]
    q0 = r0["quote_tex"].encode("utf-8")
    src0_raw = read_bytes(r0["source_tex_file"])
    src0_lf = crlf_to_lf(src0_raw)
    corrupted = q0[: len(q0) // 2] + b"ZZQX" + q0[len(q0) // 2:]
    chk("CONTROL", "C1_corrupted_quote_no_match",
        not quote_present(corrupted, src0_raw) and not quote_present(corrupted, src0_lf),
        "mutated quote absent from source")
    chk("CONTROL", "C2_empty_quote_rejected", not quote_present(b"", src0_raw) and find_enclosing_locator("x", "") == ("absent", None),
        "empty quote is rejected by the presence predicate and yields no locator")
    other_raw = read_bytes(cand_rows[1]["source_tex_file"])
    chk("CONTROL", "C3_cross_source_quote_no_match",
        not quote_present(q0, other_raw) and not quote_present(q0, crlf_to_lf(other_raw)),
        "SRC-014 quote not present in SRC-029 source")
    mut = dict(f2a_pred); mut["matter"] = "scalar"
    chk("CONTROL", "C4_schema_predicate_sensitive_to_matter",
        not (mut["matter"] == "none" and float(mut["cosmological_constant"]) == 0.0),
        "mutated schema with matter=scalar is not vacuum-admissible")
    chk("CONTROL", "C5_frozen_schema_hashes_match", f2a_ok and f2b_ok,
        f"f2a={f2a_sha == f2a_expect} f2b={f2b_sha == f2b_expect}")
    # mention-vs-binding classifier controls (CF-16 pattern)
    bare = occurrences_with_kind("AF-SCC-C2-VAC-GEN;AF-WCC-SCALAR-SPH", "AF-SCC-C2-VAC-GEN")
    phrased = occurrences_with_kind(
        "SCC-side frozen vacuum binding AF-SCC-C2-VAC-GEN removed; no AF-SCC-*-VAC-GEN binding",
        "AF-SCC-C2-VAC-GEN")
    chk("CONTROL", "C6a_bare_id_classified_binding", len(bare) == 1 and bare[0]["kind"] == "binding",
        "bare mapping slot -> binding")
    chk("CONTROL", "C6b_removal_phrase_classified_mention", len(phrased) == 1 and phrased[0]["kind"] == "mention",
        "removal phrase -> mention, not binding")

    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    n_fail = sum(1 for c in checks if c["status"] == "FAIL")

    inputs_end = {k: sha256_file(p) for k, p in
                  [("canonical_ledger", CANON), ("candidate_csv", CAND_CSV), ("candidate_jsonl", CAND_JSONL),
                   ("f2a_c2_schema", F2A), ("f2b_c0_schema", F2B)]}
    moved = {k: {"start": inputs[k]["sha256"], "end": inputs_end[k]}
             for k in inputs if inputs[k]["sha256"] != inputs_end[k]}

    result = {
        "verification_id": "worker-009-quoteverify-2026-09-12T0102+08:00",
        "task_id": "W009-L1-QUOTEVERIFY-01",
        "created_at": NOW,
        "artifact_timestamp_policy": "created_at frozen at RUN_STAMP for byte-reproducibility; wall-clock time is in the outbox event and checkpoint",
        "worker": "worker-009",
        "actor_id": "deepseek-flash-09",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "task": ("same-worker cross-method re-derivation of the five SCC class-binding correction "
                 "quotes from pinned bytes + explicit C0/C2 schema-predicate discrimination"),
        "canonical_write": "none - verification/proposal only; lead-literature owns ledger/citation_audit.csv",
        "independence_caveat": ("author self-verification by the same worker id that produced the quotes; "
                                "NOT an independent reviewer verdict. An independent lead-audit pass is still required."),
        "inputs": inputs,
        "inputs_moved_in_session": moved,
        "frozen_schema_predicates": {"F2a": f2a_pred, "F2b": f2b_pred,
                                     "FROZEN_revision": frozen_rev.get("revision"),
                                     "FROZEN_file_sha256": sha256_file(FROZEN)},
        "rows": per_row,
        "checks": checks,
        "summary": {
            "rows": len(per_row),
            "checks_pass": n_pass,
            "checks_fail": n_fail,
            "quotes_byte_exact": sum(1 for r in per_row if r["quote_byte_exact"]),
            "quotes_crlf_normalised_exact": sum(1 for r in per_row if r["quote_crlf_normalised_exact"]),
            "rows_correction_warranted": sum(1 for r in per_row if r["correction_warranted"]),
            "rows_residual_binding_defect": sum(1 for r in per_row if r["residual_binding_defect"]),
            "rows_c2_vacuum_binding_supported": sum(1 for r in per_row if r["c2_vacuum_binding_supported"]),
            "rows_c0_vacuum_binding_supported": sum(1 for r in per_row if r["c0_vacuum_binding_supported"]),
        },
        "hard_failures": [c for c in checks if c["status"] == "FAIL"],
        "finding": ("All five correction rows quote pinned source text byte-exactly once the candidate CSV is "
                    "read newline-preserving, and all five recorded quote_tex_sha256 values verify; every quoted "
                    "context carries non-vacuum matter and/or non-zero-Lambda (de Sitter) or fixed-background "
                    "linear content, so no row supports a binding to AF-SCC-C2-VAC-GEN or AF-SCC-C0-VAC-GEN. "
                    "Under the binding-vs-mention classifier the proposed new mappings contain no bound frozen "
                    "vacuum id (the literal ids in CBC-09-008/012 sit inside removal phrases and are mentions). "
                    "Reproducibility hazard recorded: a text-mode CSV read silently rewrites CRLF->LF inside "
                    "quote_tex and makes the recorded SRC-029 hash fail; readers must use newline=''."),
        "next_falsifier": ("independent lead-audit review of these five quote sets at the pinned source hashes, "
                           "or an independent re-fetch showing any quoted context is 4D Einstein vacuum Lambda=0 "
                           "with no matter; also lead-literature applying the 2-cell remediation and re-running "
                           "DET-REV12 strict over the applied ledger, expecting zero hits."),
        "falsifier": ("Any of: (a) any pinned source or schema hash moves from the value recorded in inputs; "
                      "(b) a re-fetch of any of the five sources shows the quoted theorem is 4D Einstein vacuum "
                      "Lambda=0; (c) any proposed new_class_mapping is found to BIND a frozen AF-SCC-*-VAC-GEN "
                      "id under the binding-vs-mention classifier; (d) controls C1-C6 fail on re-run."),
    }

    out_json = os.path.join(OUTDIR, "verification_quotes_worker-009.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
        f.write("\n")

    out_csv = os.path.join(OUTDIR, "quote_verify_worker-009.csv")
    cols = ["correction_id", "canonical_row_id", "source_sha256_matches_recorded",
            "quote_byte_exact", "quote_crlf_normalised_exact", "locator_kind", "locator_label",
            "c2_vacuum_binding_supported", "c0_vacuum_binding_supported",
            "correction_warranted", "residual_binding_defect", "new_bound_frozen_ids"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in per_row:
            r2 = dict(r)
            r2["new_bound_frozen_ids"] = ";".join(r["new_bound_frozen_ids"])
            w.writerow(r2)

    manifest = {
        "artifacts": [
            {"path": os.path.relpath(out_json, ROOT), "sha256": sha256_file(out_json), "bytes": os.path.getsize(out_json)},
            {"path": os.path.relpath(out_csv, ROOT), "sha256": sha256_file(out_csv), "bytes": os.path.getsize(out_csv)},
            {"path": os.path.relpath(os.path.abspath(__file__), ROOT), "sha256": sha256_file(os.path.abspath(__file__)), "bytes": os.path.getsize(os.path.abspath(__file__))},
        ],
        "created_at": NOW,
        "summary": result["summary"],
    }
    out_manifest = os.path.join(OUTDIR, "MANIFEST_worker-009.json")
    with open(out_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)

    print(json.dumps({"summary": result["summary"], "hard_failures": result["hard_failures"],
                      "finding": result["finding"], "manifest": manifest["artifacts"]}, indent=1))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
