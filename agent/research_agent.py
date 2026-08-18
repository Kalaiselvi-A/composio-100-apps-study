#!/usr/bin/env python3
"""
research_agent.py
------------------
Pass 1 of the pipeline: for a given app name + hint URL, ask a model
(with live web search) to fill in the same schema as data/apps.py.

This is the real agent -- not a mock. It calls the Anthropic Messages
API with the `web_search_20250305` server tool switched on, so the
model must ground its answer in pages it actually opens during the
call, not in training-data memory. Composio's own SDK/MCP tools can be
swapped in for the search tool with no change to the surrounding
loop -- see README.md "Swapping in Composio" for the four-line diff.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 research_agent.py --in apps_todo.json --out raw_pass1.json

apps_todo.json is a list of {"name": ..., "hint": ...} objects taken
straight from the assignment's 100-app table.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

SCHEMA_PROMPT = """You are a product-integrations researcher. Research the app below using
web search and answer ONLY with a single JSON object, no prose, matching this schema:

{{
  "name": "{name}",
  "category": "one of: CRM & Sales / Support & Helpdesk / Communications & Messaging / \
Marketing, Ads & Social / Ecommerce / Data, SEO & Scraping / Developer & Infra / \
Productivity & PM / Finance & Fintech / AI, Research & Media",
  "blurb": "what it does, <12 words",
  "auth": ["list of auth methods the docs actually state, e.g. OAuth2, API key, Basic, Bearer token"],
  "access": "self-serve | gated | mixed | blocked",
  "access_detail": "one sentence: what a developer actually has to do to get credentials",
  "api": "one sentence: REST/GraphQL/etc, and roughly how broad the surface is",
  "mcp": "official | community | preview | none",
  "verdict": "ready | ready (friction) | partial | blocked",
  "blocker": "the single biggest blocker to building an agent toolkit today, or empty string",
  "evidence": "the single URL your answer is most pinned to"
}}

If you cannot find a public developer API for this app, do not invent one -- set
access/verdict to reflect that honestly and say so in "blocker".

App: {name}
Hint: {hint}
"""

def call_model(name: str, hint: str, model: str = "claude-sonnet-4-6", timeout=90) -> dict:
    """One research call, with the web_search tool enabled server-side."""
    api_key = os.environ["ANTHROPIC_API_KEY"]
    payload = {
        "model": model,
        "max_tokens": 1024,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [
            {"role": "user", "content": SCHEMA_PROMPT.format(name=name, hint=hint)}
        ],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())

    # collect the final text block (after any tool_use/tool_result turns)
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    text = "\n".join(text_blocks)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"name": name, "error": "no JSON in model output", "raw": text[:500]}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return {"name": name, "error": f"bad JSON: {e}", "raw": match.group(0)[:500]}
    parsed["_search_calls"] = sum(1 for b in data.get("content", []) if b.get("type") == "server_tool_use")
    return parsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile", required=True)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between calls, be polite")
    args = ap.parse_args()

    with open(args.infile) as f:
        todo = json.load(f)

    results = []
    for i, item in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] researching {item['name']}...", file=sys.stderr)
        try:
            result = call_model(item["name"], item.get("hint", ""), model=args.model)
        except Exception as e:  # noqa: BLE001 -- log and keep going, don't kill the batch
            result = {"name": item["name"], "error": str(e)}
        results.append(result)
        time.sleep(args.sleep)

    with open(args.outfile, "w") as f:
        json.dump(results, f, indent=2)
    print(f"wrote {len(results)} records to {args.outfile}", file=sys.stderr)


if __name__ == "__main__":
    main()
