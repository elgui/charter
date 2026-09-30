# Rails

The road this project is on, in order. Every open unit names one item with `rail: <id>` (or a
`roadmap:` link whose anchor is the id). `charter check --rails` warns on an open unit that names
none; with `"rails": {"required": true}` in `charter/config.json` such a unit is refused when it is
in the change set. This file is the owner's: adding an item is the recorded re-plan, and
`charter rail <id> <status>` sets an item's status in one commit.

To use it, copy this file to `charter/rails.md` and replace the example rows.

Statuses: todo, next, in-progress, done, parked, dropped. Order sorts the road; ids are lower-case.
The optional `groups` column (comma-separated globs) puts every unit of a matching `group:` on
that rail unless the unit names a rail itself.

| id | title | status | order | groups |
|---|---|---|---|---|
| r1-example | The first item on the road | next | 10 | |
