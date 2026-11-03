# Owner acceptance across Charter and the Owner Desk

Charter owns protected criteria and the commit that accepts one. An owner interface owns presentation, authorization and delivery of the owner's confirmation. An action's successful execution, a human observation and a tasket's acceptance are separate records; a completion confirmation must say what it closes (`package/.charter/owner.py`, functions `owner_lines`, `acceptance_contract`, `accept`; `docs/verification.md`).

## Additive contract, package 0.4.21

`charter owner --json` adds nullable `acceptance` to its existing item fields. Owner-line items export version 1 with `unit`, `criterion`, `file`, `text`, `branch`, `expected` and `perform`. `branch` is a full symbolic ref; `expected` hashes the exact identity, location, source text and branch. Other criteria and Log entries may change independently (`acceptance_contract` in `package/.charter/owner.py`).

The completion `perform` is nested under `acceptance`, separate from the item's existing `perform`. It is an absolute argv for `charter accept UNIT AC --expected HASH`. It confirms that the criterion was satisfied; it does not perform the act described in an `owner: do` line, execute a probe, approve a proposed decision, deploy, close the whole tasket or resume a chain (`accept`, `_accept` in `package/.charter/owner.py`).

An interface may present any owner-line kind as a completion observation with the criterion's full text, project, file and branch. A positive confirmation invokes the exported completion argv once, with the owner's note and an `Owner-Action:` trailer. A negative observation leaves the box unchecked. Old packages have no completion contract: the interface must identify that limitation and prepare an upgrade rather than pretend that recording an observation closes a box (`tests/test_owner_acceptance.py`; Tele-Claude `services/owner_desk/detectors/charter.py`, `dashboard/src/components/OwnerDesk/CheckInstructions.tsx`).

## Writes and refusal

`charter accept` requires an unchanged committed tasket and exactly one unchecked owner criterion for the supplied key. It refuses changed text/location/branch, missing or ambiguous criteria, symlink targets, detached HEADs and agent sessions. The verb changes only that checkbox and appends a dated receipt to `## Log`, then commits exactly the tasket with the trailer. Other staged paths remain staged; a refused commit restores the tasket and index. A per-checkout lock serializes concurrent confirmations (`accept`, `_accept`, `_commit` in `package/.charter/owner.py`; `tests/test_owner_acceptance.py`).

The Owner Desk binds confirmation to the payload hash displayed before approval, claims the ask before invoking Charter, and records done only after a successful commit. Refusal keeps the ask open with the error. The desk does not make a second Log commit or edit protected checkboxes itself (`services/owner_desk/runner.py`, `services/owner_desk/store.py` in Tele-Claude; Tele-Claude `tests/test_owner_acceptance.py`).

Existing decision/approval/rail verbs, delegate policies and chain resumes retain their authority. Historical desk receipts without a bound completion contract are preserved and are not automatically replayed against today's criteria. Reconciliation of an old approval needs inspection of its exact scope and evidence (`docs/design/owner-delegate.md`; `docs/design/continuous-chain.md`; Tele-Claude `services/owner_desk/detectors/__init__.py`).

## Delivery

Upgrade installed projects through `docs/install.md` § Upgrade after the release is integrated. Deploy the corresponding Tele-Claude backend and dashboard separately. Source changes alone do not upgrade projects; new desk code tolerates legacy records and keeps their executable hashes unchanged (`tests/test_installer.py`; Tele-Claude `tests/test_owner_acceptance.py`, `tests/test_owner_desk_human_checks.py`).
