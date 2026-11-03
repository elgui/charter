# Desk sheet maintenance

Editable content and styles live in `docs/cheatsheet.html`; the PDF is generated from that one source. This replaces the 0.4.11 sheet with a two-page usage and maintenance reference checked against package 0.4.20 on 2026-11-03 (`package/VERSION`, `docs/assets/cheatsheet/sources.json`). It changes documentation only; acceptance writeback remains a documented gap (`services/owner_desk/runner.py` in Tele-Claude, functions `check` and `record_in_unit`).

## Evidence by workflow

| Sheet content | Reviewed sources |
|---|---|
| Daily unit work, protected owner criteria | `package/.claude/rules/charter.md`, sections Before you change code / Before you say done / What only the owner changes |
| AC identity, exported file and line | `package/.charter/owner.py`, function `owner_lines`; `package/.charter/bin/charter`, function `cmd_unit` |
| Separate verification claims and checker | `docs/verification.md`; Tele-Claude `services/step_close.py` |
| Taskets versus asks; housekeeping | Tele-Claude `docs/TASKETS.md`, section Taskets and Owner Desk |
| Desk entry points, kinds, filing, terminal | Tele-Claude `docs/OWNER_DESK.md`, sections 2, 3, 6, 8 and 10; `services/owner_desk/cli.py` |
| Acceptance writeback gap | Tele-Claude `services/owner_desk/runner.py`, functions `check`, `record_in_unit`; `services/owner_desk/detectors/charter.py`, function `item_to_ask` (answer-only fallback) |
| Upgrade and machine layer | `docs/install.md` § Upgrade; `bin/charter-pkg`, functions `do_status`, `do_fleet`; `machine/README.md` |
| Delegation and chain recovery | `docs/design/owner-delegate.md`; `package/.charter/delegate.py`; `docs/design/continuous-chain.md`; project rules |

The responsibility table describes the intended boundary. Its “Approved but still open” row identifies the integration work required, not an existing automatic writeback implementation. The generic owner-line case was checked in source; no particular AC-10/AC-11 tasket was supplied or identified. No owner response, protected checkbox, installed package or service was changed (`git diff --stat`; source references above).

## Refresh and rebuild

Run from this repository's root. Set `TC` to the Tele-Claude checkout being reviewed. Hashes detect source drift; a matching hash does not establish explanatory correctness (`docs/assets/cheatsheet/check_sources.py`).

```sh
python3 docs/assets/cheatsheet/check_sources.py --tele-claude "$TC"
node docs/assets/cheatsheet/build.cjs
pdfinfo docs/cheatsheet.pdf
pdftotext -layout docs/cheatsheet.pdf /tmp/charter-sheet.txt
```

The renderer needs Playwright (or playwright-core) and Chromium. If they are not available through Node's normal resolution, set `PLAYWRIGHT_MODULE` to the module directory and `CHROMIUM_PATH` to the browser executable. `PREVIEW_DIR=/tmp/charter-sheet-preview` optionally saves desktop and phone screenshots (`docs/assets/cheatsheet/build.cjs`). No dependency is installed into the project by this workflow.

When the freshness check names a change, review the affected workflow against its implementation, edit the HTML, update the reviewed version/date and only then replace the corresponding hashes/revisions in `sources.json`. Regenerate the PDF after every HTML change. Inspect both PDF pages and desktop/phone screenshots; keep the content readable rather than compressing it further (`docs/assets/cheatsheet/build.cjs`).

## Validation record

- Chromium rendering succeeded; both print containers fit and screen widths 1200px and 390px had no horizontal overflow (`$ node docs/assets/cheatsheet/build.cjs`, with the module/browser overrides above).
- The PDF contains two A4 pages; text extraction includes both page footers and readable punctuation (`$ pdfinfo docs/cheatsheet.pdf`; `$ pdftotext -layout docs/cheatsheet.pdf /tmp/charter-cheatsheet-text.txt`).
- PDF pages and desktop/phone renders were visually inspected. The PDF upgrade link targets the canonical repository guide; other document references remain plain text in the PDF to avoid embedding private worktree paths. HTML links target neighboring docs (`docs/cheatsheet.html`, renderer).
- Exact reviewed source hashes and checkout revisions are in `docs/assets/cheatsheet/sources.json`; generated output hashes are in `docs/assets/cheatsheet/outputs.sha256`.
