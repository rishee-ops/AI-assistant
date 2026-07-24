# Descript Agent Prompt Recipes

Copy-paste-style natural-language instructions for `prompt_project_agent`.
Keep each instruction to one logical change so results stay reviewable.

## Cleanup

- Remove all filler words (um, uh, er, "you know", crutch "like") across the
  whole composition.
- Remove false starts and repeated sentences, keeping the best take.
- Tighten every silent pause longer than 1.5 seconds.
- Remove the section that starts at "<exact transcript quote>" and ends at
  "<exact transcript quote>".

## Structure

- Rearrange so the strongest hook — "<quote>" — comes first, then the intro.
- Add chapter markers at each topic change based on the transcript.
- Trim the intro so the video reaches the main point within the first
  15 seconds.

## Captions & titles

- Add captions across the whole video, large and centered, styled for social.
- Add captions in a subtle bottom-third style for long-form YouTube.
- Add a title card at the start reading "<title>".
- Add lower-third name/title graphics for the speaker: "<name>", "<role>".

## Shorts / vertical

- Create a new 9:16 vertical composition containing only the section from
  "<quote A>" to "<quote B>", with large centered captions.
- Find the 3 most engaging ~30-second moments and make a vertical Short from
  each.

## Enhancements

- Add relevant stock b-roll over the section about "<topic>".
- Balance and enhance the audio levels across the composition.
- Add a gentle background music bed at low volume under the intro and outro.

## Notes

- After each edit, verify with `get_project` or a fresh `export_transcript`
  if the change affected wording.
- Long operations return a job — poll `wait_for_job` and report progress.
