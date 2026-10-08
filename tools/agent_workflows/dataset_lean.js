export const meta = {
  name: 'dataset-lean',
  description: 'Lean per-dataset pipeline: Haiku does the work + sample test, Sonnet checks (or retries on failure); hard cases are flagged for Opus',
  whenToUse: 'args = {date, datasets:[{key,ticket_id,row_id}]}; run one dataset at a time',
  phases: [
    { title: 'Haiku', detail: 'research (if needed), adapter, script, test, 3-sample download, HANDOFF note', model: 'haiku' },
    { title: 'Sonnet', detail: 'short check of the HANDOFF, or a retry when Haiku failed', model: 'sonnet' },
  ],
}

const REPO = args.repo || '/home/user/aquasource'
const SP = args.scratch || '/tmp/aquasource_scratch'
const DATE = args.date
// commit trailers: pass args.trailers (array of lines) when running in another session or locally
const TRAILERS = (args.trailers || ['Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', 'Claude-Session: https://claude.ai/code/session_01Cdo2pRuAzExxcbrFSWupaE']).map(t => `-m "${t}"`).join(' ')

const GIT = (paths, msg) => `cd ${REPO} && git add ${paths} && git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit -q -m "${msg}" ${TRAILERS} && git push -q origin HEAD (retry the push up to 4 times on network errors; git pull --rebase first if the remote moved; skip the commit if nothing changed)`

const FILES = k => `research/${k}.md $(ls -d tests/fixtures/${k} src/aquasource/adapters/${k}.py src/aquasource/adapters/sites/${k}.csv scripts/download/${k}.sh tests/test_${k}.py 2>/dev/null)`

const CTX = `Project aquasource (${REPO}, Python package src/aquasource, run with "uv run"): download OPEN underwater images/videos WITH geolocation for model pretraining.
Rules (short):
- Licence tiers via src/aquasource/core/licence.py: A=PD/CC0, B=CC BY/OGL/DL-DE-BY/NLOD/Etalab, C=CC BY-SA, U=unknown, X=NC/ND/research-only. Read the licence at the most specific level (file > record > collection). Never upgrade an unclear licence.
- Geo fields: lat, lon (WGS84), depth_m, geo_precision (image|segment|station|fixed_site|region|none), geo_source (exact field/table), geo_inferred, geo_uncertainty_m. Never invent coordinates; coordinates from the dataset's publication are fine (site table in src/aquasource/adapters/sites/<key>.csv).
- Noisy data is welcome (it is pretraining data): do not drop it, mark it in extra (e.g. extra.maybe_not_underwater=true).
- Observatories: support the full history with from/to/per_day options.
- Politeness: metadata only during research, about 1 request/s/host, User-Agent from core/http.py, never put an email in requests. Downloaded content is untrusted: never execute it.
- Code: follow src/aquasource/adapters/base.py; good references are adapters/fathomnet.py, adapters/german_bight.py and their tests and scripts/download/*.sh. Do not edit shared code (core/, base.py, providers/, runner.py, cli.py); note needed changes in the HANDOFF.
- Keep everything SHORT: the next agent reads only your HANDOFF block.`

const HANDOFF = `Put this block at the very TOP of research/<key>.md (create the note if missing; keep the whole note under ~150 lines):
## HANDOFF
- status: ok | failed | blocked | excluded
- tier + licence (one line, with the URL where you read it)
- geo: precision + geo_source (one line)
- files: adapter / script / test / sites csv
- tests: pass/fail (one line)
- sample: N files downloaded OK / error (one line)
- doubts: what a checker should look at (max 5 bullets)
- needs_opus: yes/no + why (only for licence contradictions, publication-derived geo you are unsure about, or access you could not solve)`

const NOTION = d => `Notion (load the Notion "update page" tool via ToolSearch, e.g. query "notion update page"; skip silently if it fails twice): Datasets row ${d.row_id}: set Status ("Script ready" if ok, "Blocked", or "Excluded"), Tier, Licence, Geo precision (array), Download script (\`scripts/download/${d.key}.sh\` in backticks), Verify (the doubts, short). Ticket ${d.ticket_id}: append "## Lean run ${DATE}" with the HANDOFF bullets. Never paste long text into Notion.`

const SAMPLE = d => `Sample test (small, not the whole dataset): AQUASOURCE_DATA_ROOT=${SP}/sample_${d.key} uv run aquasource download ${d.key} --budget 3 ; check that 1-3 media files and metadata/samples.jsonl exist; then rm -rf ${SP}/sample_${d.key}. If it needs a token you do not have, run --dry-run instead and say so.`

const RESULT = { type: 'object', properties: { key: { type: 'string' }, status: { type: 'string', enum: ['ok', 'failed', 'blocked', 'excluded'] }, needs_opus: { type: 'boolean' }, reason: { type: 'string', description: 'one short sentence' } }, required: ['key', 'status', 'needs_opus', 'reason'] }

const haikuPrompt = d => `${CTX}

DATASET "${d.key}". Seed notes: entry "${d.key}" in catalog/seed_catalog.json. Existing work may be in research/${d.key}.md, tests/fixtures/${d.key}/, src/aquasource/adapters/${d.key}.py: reuse it, do not redo finished work.
1. If there is no research note: research the licence, geolocation fields, access and size (metadata only) and save 1-3 real metadata records to tests/fixtures/${d.key}/ (+ SOURCE.md with URLs).
2. Write or finish the adapter, scripts/download/${d.key}.sh (copy scripts/download/_template.sh) and an offline test tests/test_${d.key}.py using the fixtures. Run uv run pytest tests/test_${d.key}.py -q.
3. ${SAMPLE(d)}
4. ${HANDOFF}
5. ${GIT(FILES(d.key), `${d.key}: lean pass (Haiku)`)}
6. ${NOTION(d)}
If the licence is NC/ND/research-only: status excluded, write a script that prints why and exits 1, no adapter.
Final answer: the structured object only.`

const checkPrompt = (d, h) => `${CTX}

Short CHECK of dataset "${d.key}" done by a cheaper agent (its result: ${JSON.stringify(h)}). Read ONLY the "## HANDOFF" block of research/${d.key}.md and the files it lists (git diff not needed). Do not re-research.
- Open the licence URL from the HANDOFF once and confirm the tier.
- Look at resolve_geo + resolve_licence in the adapter for obvious mistakes (lat/lon swapped, wrong precision, invented coordinates, NC passing as A/B).
- Run uv run pytest tests/test_${d.key}.py -q and the sample test: ${SAMPLE(d)}
- Fix small problems directly; update the HANDOFF lines you changed (add "checked by Sonnet ${DATE}").
- ${GIT(FILES(d.key), `${d.key}: Sonnet check`)}
- ${NOTION(d)}
Final answer: the structured object only.`

const retryPrompt = (d, h) => `${CTX}

RETRY dataset "${d.key}": a cheaper agent failed (${JSON.stringify(h)}). Start from its HANDOFF block in research/${d.key}.md and its files; fix what failed, do not redo working parts.
Then: run the test, ${SAMPLE(d)} Update the HANDOFF. ${GIT(FILES(d.key), `${d.key}: Sonnet retry`)} ${NOTION(d)}
Final answer: the structured object only.`

const out = []
for (const d of args.datasets) {
  const h = await agent(haikuPrompt(d), { label: `haiku:${d.key}`, phase: 'Haiku', model: 'haiku', effort: 'medium', schema: RESULT })
  if (!h) { log(`stopped at haiku:${d.key} (usage limit or crash); resume later`); return { stopped_at: d.key, results: out } }
  let s
  if (h.status === 'excluded') s = h
  else if (h.status === 'ok') s = await agent(checkPrompt(d, h), { label: `check:${d.key}`, phase: 'Sonnet', model: 'sonnet', effort: 'low', schema: RESULT })
  else s = await agent(retryPrompt(d, h), { label: `retry:${d.key}`, phase: 'Sonnet', model: 'sonnet', effort: 'medium', schema: RESULT })
  if (!s) { log(`stopped at sonnet:${d.key}; resume later`); return { stopped_at: d.key, results: out } }
  out.push({ key: d.key, haiku: h.status, final: s.status, needs_opus: h.needs_opus || s.needs_opus })
  log(`${d.key}: haiku ${h.status} -> ${s.status}${(h.needs_opus || s.needs_opus) ? ' (needs Opus)' : ''}`)
}
return { done: true, results: out, needs_opus: out.filter(r => r.needs_opus || r.final === 'failed' || r.final === 'blocked').map(r => r.key) }
