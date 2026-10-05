Session 1: 4 commit(s) 38d1e63..f077f48, peak context 14%
- f077f48 t2: done, evidence
- d92ebb7 t2: slugify() makes URL slugs
- ccb5860 t1: done, evidence
- 7f626bc t1: greet() says hello
Units moved:
- t1: next -> done, 1/1 criteria checked (.taskets/t1.md)
- t2: next -> done, 1/1 criteria checked (.taskets/t2.md)
Probes of t1, closed this session, re-run now: pass
  - `$ python3 -c "from app.greet import greet; assert greet('Ada') == 'Hello, Ada!'"` → exit 0
Probes of t2, closed this session, re-run now: pass
  - `$ python3 -c "from app.slug import slugify; assert slugify('Hello, World 2!') == 'hello-world-2'"` → exit 0
Gates on the session's change set (`charter check --all --base 38d1e63`): charter check: 0 blocking, 2 warning(s) [tree, track prototype, opt-ins: none]
Tree: clean
