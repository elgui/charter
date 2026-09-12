---
name: charter-progress
description: Produce the evidence-linked progress synthesis for this project. USE WHEN the user asks "where does this stand", "progress report", "what is done", "status for the client", "synthesis", OR before a client update.
---

# charter-progress

1. `python3 .charter/bin/charter ledger fold` (records this machine's ended sessions).
2. `python3 .charter/bin/charter synth --write`. It writes `charter/progress.md` only if its own anchoring check passes; if it fails, fix the unit or decision it names and rerun. Do not edit the output by hand.
3. Read it and report the sections that changed since the last synthesis (`git diff charter/progress.md`). Keep the client-facing summary to the scope section and the accepted units; the rest is for the owner. The written file leaves out gate activity, which is per machine; `charter synth` without `--write` prints it.
4. Anything you add in prose must itself pass `python3 .charter/bin/charter anchors <file>`.
