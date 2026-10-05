Session 3: 2 commit(s) 03c0c36..7b6dca1, peak context 19%
- 7b6dca1 t3: done, evidence
- 0fd2cb7 t3: median(xs)
Units moved:
- t3: next -> done, 1/1 criteria checked (.taskets/t3.md)
Probes of t3, closed this session, re-run now: pass
  - `$ python3 -c "from app.stats import median; assert median([3, 1, 2]) == 2"` → exit 0
Gates on the session's change set (`charter check --all --base 03c0c36`): charter check: 0 blocking, 1 warning(s) [tree, track prototype, opt-ins: none]
Tree: clean
