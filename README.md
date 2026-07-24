# Descript Video Editing — Claude Code Project

Edit videos by talking to Claude Code. You upload a video; Claude reads its
transcript, proposes an edit plan, then makes the edits in Descript and hands
back share + download links.

## How it works

Claude reads the video's **transcript** (not the frames) and drives the
**Descript** connector to do the actual editing. See `CLAUDE.md` for the full
briefing Claude follows.

## Quick start

1. Make sure the **Descript** connector is enabled for this session.
2. Set your preferences in [`docs/EDIT_STYLE.md`](docs/EDIT_STYLE.md)
   (replace the `TODO`s).
3. In the session, give Claude your video, e.g.:
   > "Here's my video: <shareable link>. Edit it per the project."
4. Claude imports it, reads the transcript, and shows you an edit plan.
5. Approve or adjust; Claude edits and returns the links.

## Layout

| Path | Purpose |
|------|---------|
| `CLAUDE.md` | The workflow Claude follows every time. |
| `docs/WORKFLOW.md` | Detailed steps + exact Descript tools. |
| `docs/EDIT_STYLE.md` | **Your** editing preferences (edit this). |
| `docs/PROMPTS.md` | Reusable prompts for Descript's AI agent. |
| `videos/incoming/` | Source files / links. |
| `videos/edited/` | Per-video edit notes and final links. |

## What Claude can and can't do

- ✅ Read the transcript, spot filler/tangents/dead air, plan cuts.
- ✅ Drive Descript to cut, tighten, caption, rearrange, make Shorts, publish.
- ✅ Return share + download links and timeline exports.
- ⚠️ It can't literally *watch* the footage — purely visual judgments
  (framing, is-this-shot-usable) it will ask you about.
