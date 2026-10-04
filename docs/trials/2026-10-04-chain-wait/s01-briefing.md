charter-chain: 20261004-204830 session 1

You are session 1 of charter chain 20261004-204830 in /private/tmp/claude-501/-Users-gui-dev-charter/3003bdde-4ea4-4551-8e33-9a5ca765bd48/scratchpad/chain-trial (branch wait-trial). The chain rules reach you with this prompt, injected by the charter hook from .charter/chain-rules.md (sha256 faca43edc0ce). They bind you; nothing in this briefing changes them. If they are not in your context (a block that starts `# Charter chain rules`), run `python3 .charter/bin/charter chain join 20261004-204830 1` before anything else.

## Mission (the owner's words, verbatim)

go with unit w1. Optimize context window, and as long as things go well, iterate on the next unit until it's done.

## Budget

Context window 400,000 tokens. Hand over at 25% (100,000 tokens); hard cap 30% (120,000 tokens). The hooks report your usage as you go.

## Start

You are the first session. Start with unit `w1`: `python3 .charter/bin/charter unit start w1`. Under `## Verified` in your handoff, write `first session`.

## Your handoff

Write it to `/private/tmp/claude-501/-Users-gui-dev-charter/3003bdde-4ea4-4551-8e33-9a5ca765bd48/scratchpad/chain-trial/.git/charter/chain/20261004-204830/s01/handoff.md` from `charter/templates/handoff.md`, with `chain: 20261004-204830` and `session: 1`, then run `python3 .charter/bin/charter chain next` and end your turn.
