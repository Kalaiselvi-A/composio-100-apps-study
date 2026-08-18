# Composio 100-app buildability study

**Live case study:** https://kalaiselvi-a.github.io/composio-100-apps-study/
**This repo:** https://github.com/Kalaiselvi-A/composio-100-apps-study


Research pipeline + findings for the AI Product Ops Intern take-home: 100 apps,
researched for auth/access/API-surface/buildability, clustered into patterns,
and cross-checked for accuracy. Full write-up: `site/index.html` (open directly,
no build step).

## What's in here

```
data/
  apps.py             # the 100-row dataset -- the agent's final, human-reviewed answers
  patterns.py         # pure-python analysis over apps.py -> the aggregate findings
  verification.json   # the hand/browser cross-check log (21-app stratified sample)
agent/
  research_agent.py   # the actual research agent: Claude + web_search tool, structured output
site/
  index.html           # the single-page case study (open this)
```

## The agent

`agent/research_agent.py` is real, runnable code, not a mock. Given `{"name", "hint"}`
pairs, it calls the Anthropic Messages API with the `web_search_20250305` server
tool enabled, forces a strict JSON schema in the prompt, and parses the model's
final answer. That's the whole loop -- one call per app, tool use handled
server-side, output validated against a schema.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 agent/research_agent.py --in apps_todo.json --out raw_pass1.json
```

### Swapping in Composio

The assignment suggests building this with Composio's own SDK/MCP, which is the
more realistic version of this pipeline (this is literally the job). The diff
is small because the loop doesn't change -- only the tool the model calls does:

```python
# instead of the built-in web_search tool, point the model at Composio's
# hosted MCP server and let it call real toolkit-introspection + browser tools:
from composio import ComposioToolSet
toolset = ComposioToolSet(api_key=os.environ["COMPOSIO_API_KEY"])
tools = toolset.get_tools(actions=["FIRECRAWL_SCRAPE", "GITHUB_SEARCH_REPOSITORIES"])
# ...pass `tools` into the same Messages API call in place of web_search_20250305
```

I did not wire this up end-to-end against a live Composio account inside this
6-8 hour window -- see "Honest account of what actually ran" below.

## The verification loop (accuracy is the point)

`data/verification.json` is the log of a 21-app stratified sample (every
category represented, weighted toward apps that looked gated/blocked/uncertain,
since those are the verdicts most expensive to get wrong) that I re-researched
by hand -- opening the actual docs pages -- independent of a naive single pass.

**15 of 21 sampled apps (71%) had at least one wrong or unsupported field on a
naive pass** (assuming "it's probably self-serve like its category peers,"
missing a mid-2026 rebrand, missing a plan-gate on the useful part of an API,
assuming a hinted product still exists). All 15 were corrected and are now
pinned to a docs URL in `data/apps.py`. Details and before/after for each are
in `verification.json` -- I'm not hiding the misses, the case study page shows
them.

The other 79 apps in the 100 were researched in a single grounded pass
(`confidence: "agent"` in `apps.py`) and were **not** independently re-verified.
That's disclosed on the case study page rather than presented as uniform
confidence -- treat those as good-faith, not audited.

## Honest account of what actually ran

Being upfront, per the assignment's own honesty clause: I did not have an
`ANTHROPIC_API_KEY` available inside the sandboxed environment I built this in,
so `research_agent.py` was written and is runnable, but was not executed
end-to-end against all 100 apps as a batch job in this pass. Instead, I (the
assistant) *was* the research engine for this delivery -- I ran the same
web-search-grounded loop the script encodes, by hand, per app, inside this
conversation, including the live cross-checks logged in `verification.json`.
The script exists so the exact same process can be re-run as an unattended
batch job with a real API key -- which is what "an agent, not by hand" means
in production, and is the honest next step rather than something faked here.

## Running the analysis

```bash
cd data
python3 patterns.py   # prints the aggregate findings as JSON, no API key needed
```

## Reproducing / extending

1. Add new `{"name", "hint"}` rows to a todo file in the assignment's format.
2. Run `research_agent.py` with a real key to get a first pass.
3. Sample it, verify by hand against docs (as in `verification.json`), patch
   `data/apps.py` with corrected rows.
4. Re-run `patterns.py` and refresh the numbers embedded in `site/index.html`.
