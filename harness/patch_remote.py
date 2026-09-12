from pathlib import Path
p=Path('/Users/guoshaoyang/Desktop/workdir/math/ai4math_runtime/class_separation.py')
s=p.read_text()
old='        assert_match = _MERGE_ASSERT.search(ctx)\n        if assert_match:\n            before = ctx[:assert_match.start()]\n'
new='        assert_match = _MERGE_ASSERT.search(ctx)\n        if assert_match:\n            if re.search(r"false[- ]positive|non[- ]merge|no\\s+(?:genuine\\s+)?(?:c0/c2|c2/c0)\\s+merge|not\\s+(?:a\\s+)?merge|detector\\s+(?:finding|flag)|quotes?\\s+(?:or\\s+describes?\\s+)?the\\s+detector|0\\s+genuine\\s+assertions?", ctx, re.I):\n                continue\n            before = ctx[:assert_match.start()]\n'
if old not in s: raise SystemExit('needle missing')
p.write_text(s.replace(old,new))
