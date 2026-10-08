# Agent workflows

## Lean run (current): `dataset_lean.js`

One dataset at a time, cheapest model first:

1. **Haiku** (effort medium) researches the dataset if there is no note yet, writes the adapter,
   `scripts/download/<key>.sh` and an offline test, downloads **3 samples** into a scratch folder
   (then deletes them), writes a `## HANDOFF` block at the top of `research/<key>.md`, commits and
   pushes its files and updates the Notion row and ticket.
2. **Sonnet** reads only that HANDOFF block:
   - if Haiku succeeded: a short check (effort low): licence URL, `resolve_geo` / `resolve_licence`,
     test and sample rerun;
   - if Haiku failed: a retry (effort medium) that starts from Haiku's notes.
3. Datasets flagged `needs_opus` (licence contradictions, unsure publication-derived geo,
   unsolved access) are returned at the end and handled one by one in an interactive session.

Arguments: `dataset_lean.args.json`:
- `datasets`: the queue (Go list first, then Maybe), with Notion ticket and row ids;
- `repo`: absolute path of the checkout;
- `trailers`: commit trailer lines;
- `not_queued`: finished datasets and the proposed drops (add a key to `datasets` to queue it).

If a run stops (usage limit, crash), resume it with `resumeFromRunId` and the same script and args:
finished agents are cached.

## Running it on your own machine

Everything lives in this branch and in Notion, so nothing is lost by leaving the cloud container.

```bash
git clone -b claude/festive-wright-kgoupi https://github.com/TorbenGl/aquasource.git
cd aquasource
uv sync                                   # needs uv: https://docs.astral.sh/uv/
uv run pytest -q                          # should be all green
export AQUASOURCE_DATA_ROOT=/big/disk/aquasource   # where real downloads go (images/videos/metadata per dataset)
claude                                    # logged in with your claude.ai account
```

In Claude Code:

- `/mcp` must list a Notion server. claude.ai connectors appear automatically when you are logged in
  with your claude.ai account. Otherwise add Notion yourself with
  `claude mcp add --transport http notion https://mcp.notion.com/mcp`.
- `git push` must work with your own GitHub credentials (the agents push to this branch).
- Optional, fewer permission prompts: allow `Bash(uv run:*)`, `Bash(git:*)`, `WebFetch` and the
  Notion tools in `.claude/settings.local.json`, or run in auto / accept-edits mode.

Then paste this prompt:

> Read tools/agent_workflows/README.md. Use a workflow: run tools/agent_workflows/dataset_lean.js
> with the args from tools/agent_workflows/dataset_lean.args.json, but set "repo" to the absolute
> path of this checkout and "trailers" to ["Co-Authored-By: Claude <noreply@anthropic.com>"].
> If the Workflow tool is not available, do the same with the Agent tool, one dataset at a time:
> Haiku at effort medium with the Haiku prompt from the script, then Sonnet at effort low (check)
> or medium (retry), as the script does. Keep your own context small: do not read research notes
> or code yourself. Report only a table of key / Haiku status / final status / needs_opus. If the
> run stops at a usage limit, tell me and resume it later with resumeFromRunId.

Real downloads, after a dataset's script is ready: `scripts/download/<key>.sh --dry-run`, then
`scripts/download/<key>.sh --budget N` (or without a budget for everything). Files go to
`$AQUASOURCE_DATA_ROOT/<key>/{images,videos,metadata}`.

## Earlier: `dataset_sequential.js`

The first, more thorough version (research → independent verification → implementation → review,
Sonnet/Opus agents). It finished benthicnet, pangaea_images, german_bight, noaa_ncrmp, squidle_imos,
fathomnet and usgs_cmgp, but cost about 1.2–1.5 M tokens per dataset. Arguments:
`dataset_sequential.args.json`.
