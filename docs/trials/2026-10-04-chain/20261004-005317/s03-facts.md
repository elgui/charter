Session 3: 4 commit(s) 0853aa7..82ba31c, peak context 26%
- 82ba31c t3: done, evidence
- f82c3ab t3: add mean()
- f214d69 t2: done, evidence
- 5c76971 t2: add slugify()
Units moved:
- t2: next -> done, 1/1 criteria checked (.taskets/t2.md)
- t3: next -> done, 1/1 criteria checked (.taskets/t3.md)
Probes of t2, closed this session, re-run now: pass
  - `$ python3 -c "from app.slug import slugify; assert slugify('Hello, World 2!') == 'hello-world-2'"` → exit 0
Probes of t3, closed this session, re-run now: pass
  - `$ python3 -c "from app.stats import mean; import unittest; assert mean([1, 2, 3]) == 2; unittest.TestCase().assertRaises(ValueError, mean, [])"` → exit 0
Gates on the session's change set (`charter check --all --base 0853aa7`): charter check: 0 blocking, 2 warning(s) [tree, track prototype, opt-ins: none]
Tree: clean
