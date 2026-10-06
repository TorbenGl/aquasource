# Agent workflows

`dataset_sequential.js` is the Claude Code workflow that researches, verifies, implements and
reviews each dataset **one agent at a time**. After every step the agent commits its own files
here and updates the dataset's row and ticket in Notion, so an interrupted run loses at most the
step in progress.

- Arguments: `dataset_sequential.args.json` (dataset order, Notion page ids, discovery candidates).
- Run 2026-10-06: run id `wf_9335168d-2fe`. If it stops (usage limit, container restart), resume
  with the same script and arguments; finished steps are cached and skipped.
