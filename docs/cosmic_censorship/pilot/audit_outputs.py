"""Mechanical audit for early swarm drafts; never upgrades scientific evidence."""
import json
from pathlib import Path

root = Path(__file__).parent
for path in sorted((root / "runs").glob("*.json")):
    rec = json.loads(path.read_text())
    text = rec.get("content", "")
    balanced = text.count("{") == text.count("}")
    has_scope = any(k in text.lower() for k in ("scope", "assumption", "limitation"))
    has_caveat = any(k in text.lower() for k in ("limitation", "caution", "artifact", "cannot"))
    print(f"{path.stem}: chars={len(text)} balanced_braces={balanced} scope={has_scope} caveat={has_caveat}")
