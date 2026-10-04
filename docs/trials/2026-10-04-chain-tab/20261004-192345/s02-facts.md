Session 2: 2 commit(s) f077f48..1168183, peak context 14%
- 1168183 t3: done, evidence
- a447a17 t3: mean() refuses an empty list
Units moved:
- t3: next -> done, 1/1 criteria checked (.taskets/t3.md)
Probes of t3, closed this session, re-run now: pass
  - `$ python3 -c "from app.stats import mean; import unittest; assert mean([1, 2, 3]) == 2; unittest.TestCase().assertRaises(ValueError, mean, [])"` → exit 0
Gates on the session's change set (`charter check --all --base f077f48`): charter check: 0 blocking, 1 warning(s) [tree, track prototype, opt-ins: none]
Tree: clean
