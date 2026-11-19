# Trial: a blind second assessment of the interview-trial pair (2026-11-19)

**Provisional.** Both assessors are models reading records. Neither is a human observation, and one comparison on one outcome cannot show that the rubric works.

On 18 November cx-1 rated all twelve cells of the rubric in `docs/proposals/assess-charter-quality.md` for one Tele-Claude outcome, `interview-trial`, the checkpoint where the owner runs three real interviews through the studio API. It rated two snapshots of the unit that holds the checkpoint: `before`, the unit as recorded, and `substantive`, an unadopted repair. A third snapshot, `cosmetic`, rewrote the title and added repeated prose, and changed nothing else. Before this trial, only two cells (U1 and U2) had a second, independent rating.

This trial adds a second assessor for all twelve cells on all three snapshots. The comparison was computed with `bin/charter_quality.py` at commit `bd5999b`, after `tests/test_quality_score.py` passed. The evidence text, the packet and the outputs are kept privately, outside the repository. They include the frozen declaration, both worksheets, the letter map, the prompt given to the assessor and the tool's outputs. This record carries ratings, criterion IDs, scores and a generic account of each disagreement, and no evidence text.

## How it was run

- **Declaration.** One frozen declaration covers all three snapshots, with `scope: sample` because it scores one outcome and not Tele-Claude's horizon. It records the rubric at `d37050b`, the evidence cutoff 2026-11-18T19:05:15Z, and the SHA-256 of each version of the unit and of the frozen source bundle's manifest. It also lists four holds, three of them critical: unverified predecessors, the owner's token issue, and the three real trials with the owner's observation of them. This session transcribed the holds from cx-1's brief and chose which criteria each one touches.
- **Second assessor.** Claude Opus 5.5, run as a fresh general-purpose subagent with no access to this session's context. Its packet held the twelve-question table and its rating rules (lines 11–28 of the proposal), the ten frozen sources that bear on the outcome, and a neutral note of three offline script runs. The three versions were renamed with letters drawn at random, different from the letters used in the earlier review. The packet left out the frozen copy of the unit, because it is byte-identical to `before`. The assessor saw no prior scores, no labels and no letter map, and it was told to read nothing outside the packet.
- **First assessor.** cx-1's worksheet rates `before` and `substantive`. The briefing for this session calls cx-1's transcript a Codex transcript and describes the two assessors as being from the same model family. This session did not check which model cx-1 ran on.
- **Reasons.** The tool requires a reason for every cell whose rating changes. Neither assessor supplied one: cx-1's worksheet has no reason column, and a blind assessor cannot know the order of the versions. At unblinding, this session wrote `repaired-artifact` for every rise, because only the bytes of the unit differ between the snapshots. It did so in copies of the worksheets; the originals are unchanged.

## Scores

These are points out of 100, with coverage in brackets.

| Snapshot | cx-1 | Second assessor |
|---|---|---|
| before | 62.5–70.8 (91.7%) | 45.8 (100%) |
| cosmetic | not rated on this rubric | 45.8 (100%) |
| substantive | 70.8–79.2 (91.7%) | 79.2 (100%) |
| movement, before → substantive | +8.3 demonstrated points | +33.3 demonstrated points |

| Family, before → substantive | cx-1 | Second assessor |
|---|---|---|
| Spec | 83.3 → 83.3 | 66.7 → 100.0 |
| Road | 50.0–83.3 → 50.0–83.3 | 33.3 → 66.7 |
| Rail | 100.0 → 100.0 | 83.3 → 100.0 |
| Units | 16.7 → 50.0 | 0.0 → 50.0 |

For the cosmetic version, the second assessor gave every cell the same rating as `before`. cx-1 did not rate the cosmetic version on this rubric. The earlier cold review rated only U1 and U2 for it, both 0. That review was a separate assessment and is not counted here.

## Agreement, before → substantive

Out of 24 cells (12 criteria × 2 snapshots):

- **17 agree.** Of the 22 cells that both assessors rated, 17 agree exactly and all 22 are within one point.
- **2 cells have a rating from one side only.** Both are D3, which cx-1 left unknown.
- **6 of 11 cells show the same movement.** Four are unchanged for both assessors, and U1 and U2 rise for both. The count covers the cells both assessors rated in both snapshots.

| Criterion | S1 | S2 | S3 | D1 | D2 | D3 | R1 | R2 | R3 | U1 | U2 | U3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cells agreeing | 2/2 | 1/2 | 1/2 | 2/2 | 1/2 | 0/2 | 2/2 | 2/2 | 1/2 | 2/2 | 2/2 | 1/2 |

Both assessors found the same two consequential defects in the unit and gave the repair the same credit for them. U1 and U2 go from 0 to 1 for both. One defect is a stop instruction that the rail record contradicts; the other is an acceptance check that cannot pass. The repair fixes both, and each fix earns partial credit.

## The disagreements and what each would change

The account of cx-1's side comes from the evidence it wrote for each cell. The account of the second assessor's side comes from its own evidence and notes.

| Cell | cx-1 | Second | What the difference turns on | Effect if the second rating stood |
|---|---|---|---|---|
| S2 before | 2 | 1 | cx-1 rated the specification from its own provisions. The second assessor also counted against it a term the unit relies on that its predecessor does not define. | Spec before −16.7, overall before −4.2 |
| S3 after | 1 | 2 | cx-1 kept the cell at 1 because no independent assessor had applied the examples. The second assessor ran the validator on synthetic good and wrong sets of its own and counted that as independent application. | Spec after +16.7, overall after +4.2 |
| D2 before | 1 | 0 | cx-1 gave partial credit: the predecessors are named, their completion is unverified. The second assessor counted the unit's contradicted stop instruction as a contradiction in the path. This cell carries the hold on unverified predecessors. | Road before −16.7, overall before −4.2 |
| D3 before / after | ? / ? | 0 / 1 | cx-1 left the cold-reader cell unknown until a handoff is observed. The second assessor treated its own reading as the cold reader. | Road coverage rises to 100%, and the interval closes at its lower end before and at the midpoint after |
| R3 before | 2 | 1 | cx-1 rated the rail's exit as written in the rail. The second assessor docked it because the evidence the unit points to cannot be produced. This cell carries the hold on the real trials. | Rail before −16.7, overall before −4.2 |
| U3 before | 1 | 0 | cx-1 gave the shared retry rules partial credit. The second assessor judged the unit's own resume path falsified and gave 0. | Units before −16.7, overall before −4.2 |

The second assessor's movement exceeds cx-1's by 25 demonstrated points. The disagreements explain all of it, and they fall into three groups:

- **12.5 points: which records a cell is rated from.** S2, D2 and R3 differ on whether a defect in the unit also counts against the specification, road and rail cells. cx-1 rated each of those families from its own records. The second assessor counted the unit's defects there too. The rubric does not say which reading is right, and the proposal's sentence "the same artifact may support different claims" allows either. Until the rubric says which records each family is rated from, a single repair to a unit can raise all four families. The second assessor noted this risk itself: it moved one penalty from D1 to D2 and D3 so that a single defect would not be counted in every cell.
- **8.3 points: what counts as an independent observation.** S3 and D3 differ on this. The proposal says an agent may rehearse a human path, but it leaves open whether a model's reading counts as the cold reader, and whether its synthetic run counts as independent application.
- **4.2 points: how severe one defect is within Units.** U3 differs on whether a contradicted resume instruction earns 0 or partial credit.

The two assessors nearly agree on the repaired version: 70.8–79.2 for cx-1 and 79.2 for the second assessor. The difference between the two movements is mostly a difference about the starting point, `before`, and about attribution.

## Against the first release decision

The first release decision in the proposal sets five conditions. This one comparison bears on them as follows:

- **Do independent assessors identify the same consequential defect?** Yes, on U1 and U2.
- **Does the cosmetic edit earn no credit?** Yes, for the second assessor. cx-1 has no rating to compare.
- **Does the repair change the expected behaviour?** Both assessors credit it.
- **Does missing evidence stay visible?** Only in part. The second assessor rated every cell, so its coverage is 100%, while its notes list missing records that it judged around rather than leaving the cells unknown. For D2 on `substantive` it considered `?` and chose 1. Coverage is therefore not comparable between the two assessors.
- **Can the real successor name the next act?** Not tested. No real handoff took place.

The second assessor's notes also record defects it found in the repaired version, and its doubts about the trial validator. They are kept privately with its notes. This session did not verify them, and none of them changes a rating difference above.

## Limits

- **One outcome, one pair, two assessors.** One assessor is a model reading a packet. Agreement on 17 of 24 cells does not show that the rubric is reliable.
- **The two assessors did not have the same evidence.** cx-1 worked from the whole frozen bundle and the earlier offline experiments. The second assessor had an excerpt of the rubric, ten sources and a neutral note of three runs, and ran scripts on synthetic input of its own. Some differences, S3 for example, may come from this difference in evidence rather than from the rubric.
- **The versions were not fully disguised.** The repaired version describes itself as an unadopted candidate, the cosmetic version repeats a filler paragraph eight times, and the file sizes differ. The assessor could tell the versions apart, though not which one came first.
- **One session did several jobs.** This session prepared the packet, held the letter map, supplied the reasons and mapped the holds to criteria, so these steps were not independent.
- **Blindness rests on instruction.** The assessor was told to read nothing outside its packet, and its notes cite only packet files. Nothing prevented it from reading the earlier ratings on the same machine, and this session did not check its tool calls.
- **cx-1 has no cosmetic ratings.** The earlier cold review's ratings of U1 and U2 come from another rater and are not merged here.
- **The model family question is open.** This session did not establish whether cx-1 and the second assessor are from different model families.
