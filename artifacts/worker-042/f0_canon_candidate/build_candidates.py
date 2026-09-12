#!/usr/bin/env python3
"""W042-F0-CANON-CANDIDATE-08 candidate builder (offline; no canonical path is written).

Builds two byte-minimal canonicalisation variants of the F0 taxonomy from the pin snapshot:

  A: the 6 quoted alias conclusion tokens -> VOCAB_ALIASES canonical tokens.
  B: A plus the line-153 rule prose rewrite, leaving zero alias strings.

Fail-closed: the alias-site count must equal the pre-registered count; otherwise no candidate is
written. Importable (transform helpers are used by verify_f0_candidate.py).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAP = OUT / "snapshot"
CST = timezone(timedelta(hours=8))

RUN = "W042-F0-CANON-CANDIDATE-08"
F0_REL = "research_map/formulation_taxonomy.yaml"
EXPECT_QUOTED = 6
EXPECT_PROSE = 1

ALIAS_TO_CANON = {
    "strong_cosmic_censorship_C2": "scc_c2_future_inextendibility",
    "strong_cosmic_censorship_C0": "scc_c0_future_inextendibility",
}
QUOTED_RE = re.compile(r'"(strong_cosmic_censorship_(?:C2|C0))"')
PROSE_RE = re.compile(r"strong_cosmic_censorship_C2 and _C0")
ALIAS_SUBSTR_RE = re.compile(r"strong_cosmic_censorship_C[02]")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def line_text(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    return text[start:end if end != -1 else len(text)]


def alias_substrings(text: str):
    """All alias substrings with line/col, quoted or prose."""
    out = []
    for m in ALIAS_SUBSTR_RE.finditer(text):
        out.append(
            {
                "line": line_of(text, m.start()),
                "col": m.start() - (text.rfind("\n", 0, m.start()) + 1),
                "token": m.group(0),
                "quoted": text[m.start() - 1: m.start()] == '"' and text[m.end(): m.end() + 1] == '"',
            }
        )
    return out


def _replace_quoted(text: str):
    sites = []

    def sub(m):
        tok = m.group(1)
        new = ALIAS_TO_CANON[tok]
        sites.append(
            {
                "offset": m.start(),
                "line": line_of(text, m.start()),
                "before": m.group(0),
                "after": f'"{new}"',
                "context": line_text(text, m.start()).strip(),
            }
        )
        return f'"{new}"'

    new_text = QUOTED_RE.sub(sub, text)
    return new_text, sites


def _replace_prose(text: str):
    sites = []

    def sub(m):
        new = f"{ALIAS_TO_CANON['strong_cosmic_censorship_C2']} and {ALIAS_TO_CANON['strong_cosmic_censorship_C0']}"
        sites.append(
            {
                "offset": m.start(),
                "line": line_of(text, m.start()),
                "before": m.group(0),
                "after": new,
                "context": line_text(text, m.start()).strip(),
            }
        )
        return new

    new_text = PROSE_RE.sub(sub, text)
    return new_text, sites


def transform_variant(text: str, variant: str):
    """Return (candidate_text, sites). Fail-closed on unexpected alias-site counts."""
    quoted_sites = list(QUOTED_RE.finditer(text))
    prose_sites = list(PROSE_RE.finditer(text))
    if len(quoted_sites) != EXPECT_QUOTED or len(prose_sites) != EXPECT_PROSE:
        raise ValueError(
            f"pre-registered alias counts not met: quoted {len(quoted_sites)} != {EXPECT_QUOTED}, "
            f"prose {len(prose_sites)} != {EXPECT_PROSE}"
        )
    new_text, sites = _replace_quoted(text)
    if variant == "B":
        new_text, prose = _replace_prose(new_text)
        sites = sites + prose
    elif variant != "A":
        raise ValueError(f"unknown variant {variant!r}")
    return new_text, sites


def build():
    f0 = (SNAP / F0_REL).read_text(encoding="utf-8")
    manifest = {"schema": "worker-candidate-manifest/v1", "actor": "worker-042", "run": RUN,
                "source": F0_REL, "source_sha256": sha256_bytes(f0.encode("utf-8")),
                "built_at": datetime.now(CST).isoformat(timespec="seconds"), "candidates": {}}
    for variant in ("A", "B"):
        text, sites = transform_variant(f0, variant)
        path = OUT / f"CANDIDATE_{variant}_formulation_taxonomy.yaml"
        path.write_bytes(text.encode("utf-8"))
        residue = alias_substrings(text)
        manifest["candidates"][variant] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256_bytes(text.encode("utf-8")),
            "bytes": len(text.encode("utf-8")),
            "changed_sites": sites,
            "changed_line_count": len({s["line"] for s in sites}),
            "alias_substring_residue": residue,
            "alias_substring_residue_count": len(residue),
            "status": "PASS_WITH_MENTION_RESIDUE" if residue else "PASS_FULL",
        }
    (OUT / "candidate_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    for v, c in manifest["candidates"].items():
        print(f"candidate {v}: sha256 {c['sha256']} bytes {c['bytes']} "
              f"sites {len(c['changed_sites'])} residue {c['alias_substring_residue_count']} "
              f"({c['status']})")
    return manifest


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:  # fail closed, no partial candidate claim
        print(f"BUILD FAILED: {exc}")
        sys.exit(1)
    sys.exit(0)
