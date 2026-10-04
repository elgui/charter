Session 1: 4 commit(s) 6e2d601..c8be877, peak context 20%
- c8be877 t2: done, evidence
- e052839 t2: slugify
- 033b8cb t1: done, evidence
- 180df9e t1: greet(name)
Units moved:
- t1: next -> done, 1/1 criteria checked (.taskets/t1.md)
- t2: next -> done, 1/1 criteria checked (.taskets/t2.md)
Probes of t1, closed this session, re-run now: pass
  - `$ python3 -c "from app.greet import greet; assert greet('Ada') == 'Hello, Ada!'"` → exit 0
Probes of t2, closed this session, re-run now: pass
  - `$ python3 -c "from app.slug import slugify; assert slugify('Hello, World!') == 'hello-world'"` → exit 0
Gates on the session's change set (`charter check --all --base 6e2d601`): charter check: 0 blocking, 2 warning(s) [tree, track prototype, opt-ins: none]
Tree: clean
