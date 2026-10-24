Proposed decisions currently reach owner-JSON consumers without authored context, recommendation reasons or ruling consequences. Charter 0.4.19 adds per-item contract 1, nullable why/because and consequences while preserving existing keys, ruling argv, the top-level schema and text queue.

Release versions, upgrade notes and generated maps are updated. The 709-test release run found two test assumptions: missing /bin/zsh (also fails on unchanged 0.4.18) and a hard-coded current version. The corrected affected modules pass: 29 owner-acts tests with one zsh-only skip, and 21 machine-hook tests. The other 707 cases passed before those fixture-only corrections; the full suite was not repeated.

The checked-in release handoff records commands, results and publication/upgrade boundaries in docs/proposals/owner-json-content-contract.md.
