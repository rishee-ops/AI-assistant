# Video Editing with Descript — Project Brief

This project turns Claude Code into a video editor that works through the
**Descript** connector. You upload a video; Claude reads its transcript,
proposes an edit plan, asks you what it needs, then makes the edits in
Descript and hands back share + download links.

## Important: how Claude "sees" the video

Claude **cannot watch video frames**. Descript transcribes the audio, and
Claude reads that **transcript**. So editing decisions are driven by *what is
said* — filler words, false starts, repeated takes, tangents, weak intros,
dead air. Visual/pacing edits (jump cuts, captions, b-roll, reframing) are
carried out by **Descript's own AI agent**, which Claude drives with
natural-language instructions.

When a decision genuinely needs eyes on the footage (e.g. "is this shot
usable?"), Claude will say so and ask you, rather than guessing.

## The workflow (follow this every time)

1. **Intake.** The user provides a video as a shareable URL, a direct file
   upload, or an existing Descript project. Confirm which.
2. **Import.** Use `import_media` to bring it into a Descript project (create
   one if needed). Note the project ID and composition ID
   (`get_project` returns the full composition UUIDs — always use those).
3. **Read.** Use `export_transcript` (markdown or txt) and read it fully.
4. **Plan.** Produce a concrete edit plan: what to remove, tighten, or keep,
   with transcript quotes/timestamps so the user knows exactly what changes.
   Follow the defaults in `docs/EDIT_STYLE.md`.
5. **Confirm.** Show the plan. Unless `EDIT_STYLE.md` says otherwise, wait for
   approval before cutting anything destructive.
6. **Edit.** Drive `prompt_project_agent` with clear, specific instructions
   (see `docs/PROMPTS.md` for reusable prompt recipes). Do one logical change
   at a time so it's reviewable.
7. **Publish.** Use `publish_project` and **always show the user the returned
   share and download URLs.** For handoff to another editor, use
   `export_timeline`.
8. **Record.** Save the edit plan and links as a note in `videos/edited/`.

## Guardrails

- Never delete or overwrite the user's source media. Edits happen on the
  Descript composition, not the original file.
- Destructive cuts (removing content, big trims) need user sign-off first
  unless `EDIT_STYLE.md` sets a more aggressive default.
- One change at a time; report what changed after each step.
- Always surface the share/download links — don't just say "done".
- Long operations run as Descript jobs; poll with `wait_for_job` and report
  progress.

## Where things live

- `docs/EDIT_STYLE.md` — the user's editing preferences (edit this to change
  defaults). Claude reads this before proposing any plan.
- `docs/WORKFLOW.md` — the detailed step-by-step, with the exact tools.
- `docs/PROMPTS.md` — reusable natural-language prompts for Descript's agent.
- `videos/incoming/` — drop source files / links here.
- `videos/edited/` — per-video edit notes and final links.
