from pathlib import Path
p=Path('/Users/guoshaoyang/Desktop/workdir/math/ai4math_runtime/class_separation.py')
s=p.read_text()
needle='        assert_match = _MERGE_ASSERT.search(ctx)\n        if assert_match:\n            before = ctx[:assert_match.start()]\n'
repl='        assert_match = _MERGE_ASSERT.search(ctx)\n        if assert_match:\n            if re.search(r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge|detector\s+(?:finding|flag)", ctx, re.I):\n                continue\n            before = ctx[:assert_match.start()]\n'
if needle not in s: raise SystemExit('needle not found')
s=s.replace(needle,repl)
p.write_text(s)
