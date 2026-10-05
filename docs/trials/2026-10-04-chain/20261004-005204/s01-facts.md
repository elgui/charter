Session 1: 4 commit(s) 9757ab8..bb135c7, peak context 20%
- bb135c7 t3: mean() refuses an empty list
- 4e5781b t2: slugify() makes URL slugs
- abbf6e2 t1: drop pycache
- c9f351a t1: greet() says hello
Units moved:
- t1: next -> done, 1/1 criteria checked (.taskets/t1.md)
- t2: next -> done, 1/1 criteria checked (.taskets/t2.md)
- t3: next -> done, 1/1 criteria checked (.taskets/t3.md)
Probes of t1, closed this session, re-run now: pass
  - `$ python3 -c "from app.greet import greet; assert greet('Ada') == 'Hello, Ada!'"` → exit 0
Probes of t2, closed this session, re-run now: pass
  - `$ python3 -c "from app.slug import slugify; assert slugify('Hello, World 2!') == 'hello-world-2'"` → exit 0
Probes of t3, closed this session, re-run now: pass
  - `$ python3 -c "from app.stats import mean; import unittest; assert mean([1, 2, 3]) == 2; unittest.TestCase().assertRaises(ValueError, mean, [])"` → exit 0
Gates on the session's change set (`charter check --all --base 9757ab8`): charter check: 0 blocking, 3 warning(s) [tree, track prototype, opt-ins: none]
Tree: clean
