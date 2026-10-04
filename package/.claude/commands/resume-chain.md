---
description: "Owner only: resume the paused charter chain, closing the owner lines you name, with your note"
argument-hint: "[AC-n ...] [note]"
disable-model-invocation: true
---

The charter hook did not catch this command, so the chain was NOT resumed and no owner line was closed. Tell the owner exactly that in one line, and that the charter hooks may be missing or untrusted in this session (`python3 .charter/bin/charter chain status` shows the chain). Do nothing else: do not run `charter chain resume`, do not edit an `— owner:` line, do not touch `.git/charter/chain/`.
