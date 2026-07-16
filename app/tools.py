"""Tools available to the agents (Agent Loop).

Supports Mock Search, Tavily, Brave Search, Serper, and Google Custom Search APIs.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

# A mock database of search results to make the agent loop functional and offline-capable
_SEARCH_DATABASE = {
    "loop engineering": [
        {
            "title": "The Art of Loop Engineering - LangChain Blog",
            "url": "https://www.langchain.com/blog/the-art-of-loop-engineering",
            "snippet": "Loop engineering is a design pattern for AI agents consisting of four layers: the Agent Loop, the Verification Loop, the Event-Driven Loop, and the Hill Climbing Loop."
        },
        {
            "title": "Loopcraft: The Art of Stacking Loops",
            "url": "https://www.latent.space/p/ainews-loopcraft",
            "snippet": "Stacking loops improves agent reliability. While LLMs call tools in loop 1, loop 2 grades the output, loop 3 acts on events, and loop 4 analyzes traces to update system prompts."
        }
    ],
    "ai agents": [
        {
            "title": "Autonomous Agents in Production",
            "url": "https://example.com/agents-prod",
            "snippet": "Production agents need guardrails. Without token limiters, cost monitoring, and loop detection, agents can go into runaway infinite execution loops."
        },
        {
            "title": "The Shift to Agentic Workflows",
            "url": "https://example.com/agentic-workflows",
            "snippet": "Andrew Ng discusses agentic workflows. Design patterns like reflection, tool use, planning, and multi-agent collaboration outperform zero-shot prompting."
        }
    ],
    "local llms": [
        {
            "title": "Running Local Models: Ollama vs LM Studio",
            "url": "https://example.com/local-llms-guide",
            "snippet": "Ollama and LM Studio make it easy to host LLMs locally. Ollama supports grammar-constrained decoding, helping local models yield valid, schema-conforming JSON."
        }
    ]
}


def _run_mock_search(query: str) -> list[dict[str, str]]:
    """Mock search fallback."""
    query_lower = query.lower()
    results = []
    
    for key, items in _SEARCH_DATABASE.items():
        if key in query_lower:
            results.extend(items)
            
    if not results:
        results = [
            {
                "title": f"Understanding {query} - Tech Insights",
                "url": f"https://example.com/insights/{query.replace(' ', '-')}",
                "snippet": f"A deep dive analysis into {query}. Explores the core concepts, industry implications, and best practices for engineers and developers."
            },
            {
                "title": f"Practical guide to {query}",
                "url": "",
                "snippet": f"Practical implementation steps for {query}, highlighting major advantages and potential pitfalls in production systems."
            }
        ]
    return results


def _call_tavily(query: str, api_key: str) -> list[dict[str, str]]:
    """Call Tavily Search API using urllib."""
    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"api_key": api_key, "query": query, "max_results": 3}).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=8) as response:
        res = json.loads(response.read().decode("utf-8"))
        
    results = []
    for item in res.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", "")
        })
    return results


def _call_brave(query: str, api_key: str) -> list[dict[str, str]]:
    """Call Brave Search API using urllib."""
    q_encoded = urllib.parse.quote_plus(query)
    url = f"https://api.search.brave.com/res/v1/web/search?q={q_encoded}&count=3"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=8) as response:
        res = json.loads(response.read().decode("utf-8"))
        
    results = []
    web_results = res.get("web", {}).get("results", [])
    for item in web_results:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("description", "")
        })
    return results


def _call_serper(query: str, api_key: str) -> list[dict[str, str]]:
    """Call Serper (Google Search) API using urllib."""
    url = "https://google.serper.dev/search"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    data = json.dumps({"q": query, "num": 3}).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=8) as response:
        res = json.loads(response.read().decode("utf-8"))
        
    results = []
    for item in res.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", "")
        })
    return results


def _call_google(query: str, api_key: str, cse_id: str) -> list[dict[str, str]]:
    """Call Google Custom Search JSON API using urllib."""
    q_encoded = urllib.parse.quote_plus(query)
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={q_encoded}&num=3"
    
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=8) as response:
        res = json.loads(response.read().decode("utf-8"))
        
    results = []
    for item in res.get("items", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", "")
        })
    return results


def search_web(query: str) -> list[dict[str, str]]:
    """Search the web using the configured provider.
    
    Checks environment variable SEARCH_PROVIDER.
    If not explicitly set, auto-detects based on available API keys:
    - TAVILY_API_KEY -> Tavily
    - BRAVE_API_KEY -> Brave Search
    - SERPER_API_KEY -> Serper
    - GOOGLE_API_KEY & GOOGLE_CSE_ID -> Google Custom Search
    
    Falls back to mock database on failure.
    """
    provider = os.getenv("SEARCH_PROVIDER", "").lower()
    
    # Auto-detect if provider not specified
    tavily_key = os.getenv("TAVILY_API_KEY")
    brave_key = os.getenv("BRAVE_API_KEY")
    serper_key = os.getenv("SERPER_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    google_cse = os.getenv("GOOGLE_CSE_ID")
    
    if not provider:
        if tavily_key:
            provider = "tavily"
        elif brave_key:
            provider = "brave"
        elif serper_key:
            provider = "serper"
        elif google_key and google_cse:
            provider = "google"
        else:
            provider = "mock"
            
    print(f"[tools.py] executing search using provider: {provider}")
    
    try:
        if provider == "tavily" and tavily_key:
            return _call_tavily(query, tavily_key)
        elif provider == "brave" and brave_key:
            return _call_brave(query, brave_key)
        elif provider == "serper" and serper_key:
            return _call_serper(query, serper_key)
        elif provider == "google" and google_key and google_cse:
            return _call_google(query, google_key, google_cse)
    except Exception as exc:
        print(f"[tools.py] Warning: Real search call ({provider}) failed: {exc}. Falling back to mock search.")
        
    return _run_mock_search(query)
