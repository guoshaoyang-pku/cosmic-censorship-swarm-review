#!/usr/bin/env python3
"""Worker 09 / P5: HTML -> text extraction for the two quarantined pointers.

Inputs : artifacts/worker-09/sources/{full5_1901.07996.html,full5_grqc0503112.html}
Outputs: artifacts/worker-09/extracted/pointers/{grant2019.txt,rendall2005.txt}
         artifacts/worker-09/extracted/pointers/pointer_excerpts.json
Deterministic, stdlib-only. Records the sha256 of each raw input; no physics claim is
made here, the script only transcribes what the cached primary source says.
"""
from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sources"
OUT = ROOT / "extracted" / "pointers"
OUT.mkdir(parents=True, exist_ok=True)

BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br", "tr",
         "section", "article", "blockquote", "table", "figcaption", "pre"}
SKIP = {"script", "style", "noscript", "svg"}


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip_depth += 1
        if self.skip_depth == 0 and tag in BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP and self.skip_depth:
            self.skip_depth -= 1
        if self.skip_depth == 0 and tag in BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = raw.replace("\u00a0", " ").replace("\u2019", "'").replace("\u2013", "-")
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.splitlines()]
        out: list[str] = []
        for ln in lines:
            if ln:
                out.append(ln)
            elif out and out[-1] != "":
                out.append("")
        return "\n".join(out)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(name: str, html_name: str, keywords: list[str]) -> dict:
    src = SRC / html_name
    text = TextParser()
    text.feed(src.read_text(errors="replace"))
    body = text.text()
    dst = OUT / name
    dst.write_text(body)
    excerpts = []
    for kw in keywords:
        for m in re.finditer(re.escape(kw), body, re.IGNORECASE):
            lo = max(0, body.rfind("\n", 0, max(0, m.start() - 400)))
            hi = body.find("\n", min(len(body), m.end() + 400))
            excerpts.append({"keyword": kw, "char": m.start(),
                             "excerpt": body[lo:hi].strip()[:1200]})
    return {"source": html_name, "source_sha256": sha256(src), "text_out": str(dst.relative_to(ROOT)),
            "text_sha256": sha256(dst), "chars": len(body), "excerpts": excerpts}


report = {
    "grant2019": run("grant2019.txt", "full5_1901.07996.html",
                     ["not open", "curve class", "Lipschitz", "chronological future", "Theorem", "Proposition"]),
    "rendall2005": run("rendall2005.txt", "full5_grqc0503112.html",
                       ["Cauchy horizon", "Taub-NUT", "extended", "extendible", "maximal Cauchy development"]),
}
(OUT / "pointer_excerpts.json").write_text(json.dumps(report, indent=1))
for k, v in report.items():
    print(k, v["source_sha256"][:16], v["chars"], "chars", len(v["excerpts"]), "excerpts")
