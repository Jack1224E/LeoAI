"""
R2F Web Curator — Ground Truth Engine
======================================
Queries a local SearXNG instance for real-time web data and compresses
the results into dense, atomic facts for injection into the manifold
embedding and solver prompts.

Falls back to public SearXNG instances if the local one is unreachable.
"""

from __future__ import annotations

import asyncio
import re
from typing import List, Dict, Optional

import httpx

# Primary: local Docker instance. Fallbacks: public SearXNG instances.
SEARXNG_ENDPOINTS = [
    "http://localhost:8080",
    "https://search.ononoki.org",
    "https://searx.tiekoetter.com",
    "https://search.sapti.me",
]

HEADERS = {
    "User-Agent": "LeoAI-R2F/1.0 (Ground Truth Curator)",
    "Accept": "application/json",
}


async def _try_search(
    client: httpx.AsyncClient,
    base_url: str,
    query: str,
    limit: int,
) -> Optional[List[Dict[str, str]]]:
    """Attempt a search against a single SearXNG endpoint."""
    try:
        resp = await client.get(
            f"{base_url}/search",
            params={"q": query, "format": "json", "language": "en"},
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        results = data.get("results", [])[:limit]

        extracted = []
        for r in results:
            extracted.append({
                "title": r.get("title", "").strip(),
                "url": r.get("url", "").strip(),
                "snippet": r.get("content", "").strip(),
            })
        return extracted if extracted else None

    except (httpx.RequestError, httpx.HTTPStatusError, Exception):
        return None


def _compress_to_atomic_facts(results: List[Dict[str, str]]) -> List[str]:
    """Compress search results into dense, atomic facts (under 20 tokens each)."""
    facts = []
    for r in results:
        title = r["title"]
        snippet = r["snippet"]

        # Extract the most information-dense sentence from the snippet
        sentences = re.split(r'[.!?]+', snippet)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if sentences:
            # Take the first substantive sentence and compress it
            best = sentences[0]
            # Truncate to ~20 tokens (roughly 80 chars)
            if len(best) > 100:
                best = best[:97] + "..."
            facts.append(f"[{title[:50]}] {best}")
        elif title:
            facts.append(f"[SOURCE] {title[:80]}")

    return facts


async def fetch_ground_truth(query: str, limit: int = 5) -> str:
    """
    Query SearXNG for real-time ground truth data.

    Returns a formatted string block ready for injection into LLM prompts.
    Tries local instance first, falls back to public instances.
    """
    async with httpx.AsyncClient() as client:
        results = None
        used_endpoint = None

        for endpoint in SEARXNG_ENDPOINTS:
            results = await _try_search(client, endpoint, query, limit)
            if results:
                used_endpoint = endpoint
                break

        if not results:
            return (
                "=== REAL-TIME GROUND TRUTH ===\n"
                "[UNAVAILABLE] No search results could be fetched. "
                "Proceeding with model's internal knowledge only.\n"
                "=== END GROUND TRUTH ===\n"
            )

        facts = _compress_to_atomic_facts(results)

        output = "=== REAL-TIME GROUND TRUTH ===\n"
        output += f"Source: {used_endpoint} | Query: \"{query}\"\n"
        for i, fact in enumerate(facts, 1):
            output += f"  {i}. {fact}\n"
        output += "=== END GROUND TRUTH ===\n"

        return output
