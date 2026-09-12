#!/usr/bin/env python3
"""Worker 09 / L1: extract auditable metadata and theorem statements from cached sources.

Inputs : artifacts/worker-09/sources/  (raw HTML/PDF/JSON fetched by fetch_sources.sh)
Outputs: artifacts/worker-09/extracted/source_index.json
         artifacts/worker-09/extracted/theorems/<key>.txt   (numbered theorem segments)
         artifacts/worker-09/extracted/abs_meta.json       (arXiv abs-page metadata)

Deterministic, stdlib-only. pypdf is optional (used only for PDFs).
Every record carries the sha256 of the raw file it was derived from, so a reviewer can
re-run the extraction and diff. No claim about physics is made here: this script only
transcribes what the cached primary source says.
"""
from __future__ import annotations

import hashlib
import html as html_mod
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sources"
OUT = ROOT / "extracted"
THM = OUT / "theorems"

BLOCK_TAGS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br", "tr", "td",
    "section", "article", "blockquote", "table", "figure", "figcaption", "pre",
}
SKIP_TAGS = {"script", "style", "noscript", "svg"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class TheoremTextParser(HTMLParser):
    """Minimal HTML -> text converter that marks LaTeXML theorem environments."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.theorem_stack: list[dict] = []  # each: {"depth": int, "tag": str}

    # -- helpers ---------------------------------------------------------
    def _emit(self, text: str) -> None:
        if self.skip_depth == 0 and text:
            self.parts.append(text)

    def _newline(self) -> None:
        if self.skip_depth == 0:
            self.parts.append("\n")

    # -- HTMLParser interface -------------------------------------------
    def handle_starttag(self, tag: str, attrs) -> None:
        classes = ""
        for k, v in attrs:
            if k == "class" and v:
                classes = v
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if "ltx_theorem" in classes:
            self.theorem_stack.append({"tag": tag, "depth": 0})
            self._emit("\n@@THM_START@@ ")
        if tag in BLOCK_TAGS:
            self._newline()

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag == "br":
            self._newline()

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if self.theorem_stack:
            top = self.theorem_stack[-1]
            if top["tag"] == tag:
                self.theorem_stack.pop()
                self._emit(" @@THM_END@@\n")
            # nested same-name tags inside a theorem body are rare; ignore
        if tag in BLOCK_TAGS:
            self._newline()

    def handle_data(self, data: str) -> None:
        self._emit(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = html_mod.unescape(raw)
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n", raw)
        return raw


def html_to_text(path: Path) -> str:


    p = TheoremTextParser()
    p.feed(path.read_text(errors="replace"))
    p.close()
    return p.text()


def clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def abs_meta(path: Path) -> dict:
    """Pull title/authors/abstract/journal-ref/DOI out of an arXiv abs page."""
    t = html_to_text(path)
    out: dict = {"source_file": path.name, "sha256": sha256(path)}
    m = re.search(r"Title:\s*(.+?)(?:\n|Authors:|$)", t)
    if m:
        out["title"] = clean(m.group(1))
    m = re.search(r"Authors:\s*(.+?)(?:\n|Abstract:|Comments:|$)", t)
    if m:
        out["authors"] = clean(m.group(1))
    m = re.search(r"Abstract:\s*(.+?)(?:\n\s*Comments:|\n\s*Subjects:|\n\s*Cite as:)", t, re.S)
    if m:
        out["abstract"] = clean(m.group(1))
    m = re.search(r"Journal reference:\s*(.+?)(?:\n|Related DOI|$)", t)
    if m:
        out["journal_ref"] = clean(m.group(1))
    m = re.search(r"Related DOI:\s*(https?://\S+)", t)
    if m:
        out["related_doi"] = m.group(1)
    m = re.search(r"arXiv-issued DOI via DataCite", t)
    out["arxiv_doi_issued"] = bool(m)
    m = re.search(r"\[Submitted on ([^\]]+)\]", t)
    if m:
        out["submitted"] = clean(m.group(1))
    return out


def openalex_meta(path: Path) -> dict:
    d = json.loads(path.read_text())
    inv = d.get("abstract_inverted_index") or {}
    abstract = None
    if inv:
        pos: dict[int, str] = {}
        for word, idxs in inv.items():
            for i in idxs:
                pos[i] = word
        abstract = " ".join(pos[i] for i in sorted(pos))
    loc = d.get("primary_location") or {}
    source = (loc.get("source") or {}) if isinstance(loc, dict) else {}
    return {
        "source_file": path.name,
        "sha256": sha256(path),
        "title": d.get("title"),
        "doi": d.get("doi"),
        "year": d.get("publication_year"),
        "venue": source.get("display_name"),
        "volume": d.get("biblio", {}).get("volume"),
        "first_page": d.get("biblio", {}).get("first_page"),
        "last_page": d.get("biblio", {}).get("last_page"),
        "authors": [a["author"]["display_name"] for a in d.get("authorships", [])],
        "is_oa": (d.get("open_access") or {}).get("is_oa"),
        "oa_url": (d.get("open_access") or {}).get("oa_url"),
        "abstract": abstract,
    }


THM_RE = re.compile(
    r"(Theorem|Corollary|Proposition|Lemma)\s+(\d+(?:\.\d+)?)\s*[\.\):]?\s*", re.I
)


def theorem_segments(text: str, max_segments: int = 200) -> list[dict]:
    """Split marked theorem environments, falling back to regex on plain text."""
    segs = []
    marked = re.findall(r"@@THM_START@@(.*?)@@THM_END@@", text, re.S)
    if marked:
        for seg in marked[:max_segments]:
            seg = clean(seg)
            m = THM_RE.search(seg)
            if not m:
                continue
            segs.append({
                "kind": m.group(1).lower(), "number": m.group(2),
                "env": "latexm", "statement": seg[:1600],
            })
        return segs
    # fallback: raw regex windows
    for m in list(THM_RE.finditer(text))[:max_segments]:
        start = m.start()
        seg = clean(text[start:start + 1400])
        segs.append({
            "kind": m.group(1).lower(), "number": m.group(2),
            "env": "regex-window", "statement": seg,
        })
    return segs


def pdf_text(path: Path) -> str:
    try:
        sys.path.insert(0, str(ROOT / "pylibs"))
        import pypdf  # type: ignore
    except Exception as e:  # pragma: no cover
        return f"@@PDF_UNREADABLE@@ {e}"
    try:
        reader = pypdf.PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages):
            try:
                pages.append(page.extract_text() or "")
            except Exception as e:
                pages.append(f"@@PAGE_{i}_ERROR@@ {e}")
        return "\n".join(pages)
    except Exception as e:  # pragma: no cover
        return f"@@PDF_UNREADABLE@@ {e}"


def main() -> int:
    THM.mkdir(parents=True, exist_ok=True)
    index: dict = {}
    abs_all: dict = {}

    # 1. abs metadata
    for p in sorted(SRC.glob("abs_*.html")):
        key = p.name[len("abs_"):-len(".html")]
        abs_all[key] = abs_meta(p)

    # 2. openalex metadata
    for p in sorted(SRC.glob("openalex_*.json")):
        key = p.name[len("openalex_"):-len(".json")]
        index.setdefault(key, {})["openalex"] = openalex_meta(p)

    # 3. full-text theorem segments
    for p in sorted(list(SRC.glob("full_*.html")) + list(SRC.glob("full2_*.html"))
                    + list(SRC.glob("full3_*.html")) + list(SRC.glob("full4_*.html"))):
        key = p.name
        for pre in ("full_", "full2_", "full3_", "full4_"):
            if key.startswith(pre):
                key = key[len(pre):]
                break
        key = key[:-len(".html")]
        text = html_to_text(p)
        segs = theorem_segments(text)
        (THM / f"{key}.txt").write_text("\n\n".join(
            f"[{s['kind']} {s['number']}] {s['statement']}" for s in segs) or "(no theorem env found)")
        index.setdefault(key, {})["full_text"] = {
            "source_file": p.name, "sha256": sha256(p),
            "n_theorem_segments": len(segs),
            "theorem_numbers": sorted({f"{s['kind']} {s['number']}" for s in segs}),
            "dump": f"extracted/theorems/{key}.txt",
        }

    # 4. PDFs
    for p in sorted(SRC.glob("pdf_*.pdf")):
        key = p.name[len("pdf_"):-len(".pdf")]
        text = pdf_text(p)
        segs = theorem_segments(text)
        (THM / f"{key}.txt").write_text("\n\n".join(
            f"[{s['kind']} {s['number']}] {s['statement']}" for s in segs) or "(no theorem env found)")
        index.setdefault(key, {})["pdf"] = {
            "source_file": p.name, "sha256": sha256(p),
            "n_theorem_segments": len(segs),
            "theorem_numbers": sorted({f"{s['kind']} {s['number']}" for s in segs}),
            "dump": f"extracted/theorems/{key}.txt",
        }

    (OUT / "abs_meta.json").write_text(json.dumps(abs_all, indent=2, sort_keys=True))
    (OUT / "source_index.json").write_text(json.dumps(index, indent=2, sort_keys=True))
    print(f"wrote {OUT/'source_index.json'} ({len(index)} keys) and {OUT/'abs_meta.json'}")
    for k in sorted(index):
        ft = index[k].get("full_text") or index[k].get("pdf") or {}
        print(f"  {k:24s} segments={ft.get('n_theorem_segments', '-'):>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
