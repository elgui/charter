# Bug reports

Bugs in charter itself (engine, gates, installer, survey) seen from a project's session. That session writes the report here and does not fix charter; the fix happens in a session on this repository, with a test.

## One file per bug

`YYYY-MM-DD-<slug>.md`, dated the day it was seen. The slug names the symptom, not the suspected cause.

```markdown
# <symptom, one line>

- Seen: <date>, <project> at <commit>, charter <version>
- Status: open | fixed in <commit> | not a bug (<why>)

## What happened

What ran, what it printed (quote the lines), what was expected instead.

## Reproduce

The shortest command sequence that shows it, from a fresh clone where possible.

## Where

`path:line` in this repository for the code involved, as read on the day. Mark anything not read as (inference).

## Workaround

What the project did, or can do, until the fix. "None needed" is an answer.

## Suggested fix

Optional. A direction, not a patch; the fixing session decides.
```

## Rules

- Quote output; don't paraphrase it. Cite the command it came from.
- No secrets, prices or client content: a report may be read from any project.
- When fixed, set `Status:` to the fixing commit and name the test that pins it. Keep the file.
