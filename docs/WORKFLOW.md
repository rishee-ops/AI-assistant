# Detailed Workflow

The exact steps and Descript tools for editing one video.

## 0. Discover / set up the drive

- `list_projects` — see existing Descript projects and their IDs.
- `list_folders` — browse the folder hierarchy if organizing by folder.

## 1. Intake

Ask the user how the video arrives:
- **Shareable URL** (Google Drive, Dropbox, S3, etc.) — easiest.
- **Direct file upload** into the session.
- **Already in Descript** — get the project ID and skip to step 3.

## 2. Import

- `import_media` with the URL(s) or uploaded file. This can also create an
  empty project. Give the project a clear name (e.g. the video's title).
- `get_project` — retrieve the project summary. **Copy the composition UUID**
  from here; every later tool call that needs `composition_id` uses it.

## 3. Read the transcript

- `export_transcript` with format `markdown` (readable) or `srt` (has
  timestamps — useful for referencing exact moments).
- Read the whole thing. Note: filler words, false starts, repeated takes,
  tangents, weak opening, long pauses, off-topic sections, strong soundbites.

## 4. Build the edit plan

Write the plan against `docs/EDIT_STYLE.md`. Structure it as:
- **Cuts** — quote the exact lines to remove and why.
- **Tighten** — sections to condense.
- **Keep** — the spine of the video.
- **Enhancements** — captions, chapter titles, intro/outro, b-roll requests.
- **Estimated result** — rough new length.

## 5. Confirm

Show the plan. Wait for approval on destructive changes unless the style
guide authorizes proceeding automatically.

## 6. Execute edits

Use `prompt_project_agent` with specific instructions. Do one logical change
per call so each is reviewable. See `docs/PROMPTS.md` for recipes. Examples:
- "Remove all filler words (um, uh, like, you know) across the composition."
- "Remove the section from '<quote A>' through '<quote B>'."
- "Add captions styled for social, large and centered."
- "Tighten pauses longer than 1.5 seconds."

Long edits return a **job**; poll with `wait_for_job` and report progress.
If something goes wrong, `list_jobs` / `cancel_job`.

## 7. Publish & deliver

- `publish_project` → **always display the returned share + download URLs.**
- For a vertical Short, ask Descript's agent to create a 9:16 composition of
  the chosen clip, then publish that composition.
- To hand off to Premiere/Resolve/etc., `export_timeline` (returns a job →
  `wait_for_job` → show `result.download_url`).

## 8. Record the result

Write a short note in `videos/edited/<video-name>.md` with the final edit
plan, the composition ID, and the share/download links, so the history is
tracked in git.
