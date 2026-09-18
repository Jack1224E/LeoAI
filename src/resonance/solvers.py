"""
R2F Module 2 — Parallel Eigen-Solvers
=======================================
Spawns K independent LLM sessions in parallel via asyncio.gather.
Each session receives the full manifold ψ₀ but is strictly bound to
one perspective φᵢ.  Absolute isolation — instances cannot communicate.

Output schema per instance:
{
  "perspective": str,
  "projection": str,         # The actual reasoned answer from this angle
  "confidence": float,       # Self-assessed 0-1
  "conflict_points": list,   # Where this view contradicts likely alternatives
  "insight_novelty": str     # What's surprising from this angle
}
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.resonance.manifold import ConceptualEmbedding, Perspective
from src.tools.web_curator import fetch_ground_truth


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class Projection:
    """Output of a single eigen-solver instance."""
    perspective: str
    projection: str
    confidence: float
    conflict_points: List[str]
    insight_novelty: str
    raw_response: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "perspective": self.perspective,
            "projection": self.projection,
            "confidence": self.confidence,
            "conflict_points": self.conflict_points,
            "insight_novelty": self.insight_novelty,
        }


# ---------------------------------------------------------------------------
# Solver Prompt Template
# ---------------------------------------------------------------------------

SOLVER_PROMPT_TEMPLATE = """You are operating under a strict single-perspective constraint.

{ground_truth}

STRICT GROUNDING RULE: You MUST anchor your analysis in the real-time ground truth above. You are FORBIDDEN from hallucinating deprecated APIs, non-existent libraries, or physics that contradict the curated search results. If a fact from the ground truth contradicts your training data, the ground truth wins.

PROBLEM:
{problem}

CONCEPTUAL EMBEDDING (ψ₀):
- Domain: {domain}
- Transformation: {transformation}
- Constraints: {constraints}
- Key Uncertainty: {info_gradient}

YOUR ASSIGNED PERSPECTIVE: {perspective_name}
DIRECTIVE: {perspective_directive}

Analyze the problem EXCLUSIVELY through your assigned perspective. Do not attempt to be balanced or comprehensive — be maximally committed to your angle.

Respond ONLY with valid JSON — no markdown fences, no extra text:
{{
  "perspective": "{perspective_name}",
  "projection": "<your full reasoned analysis from this angle, 200-400 words>",
  "confidence": <float 0.0-1.0, how confident you are this angle captures the core truth>,
  "conflict_points": ["<point where your view likely contradicts other angles>", "..."],
  "insight_novelty": "<the single most surprising or non-obvious insight from your angle>"
}}"""


# ---------------------------------------------------------------------------
# Single Solver
# ---------------------------------------------------------------------------

async def _solve_one(
    problem: str,
    embedding: ConceptualEmbedding,
    perspective: Perspective,
    session_manager,
    timeout: float = 90.0,
) -> Projection:
    """Run a single eigen-solver instance for one perspective."""

    # Fetch perspective-specific ground truth
    search_query = f"{perspective.name} {problem[:80]}"
    ground_truth = await fetch_ground_truth(search_query, limit=3)

    prompt = SOLVER_PROMPT_TEMPLATE.format(
        problem=problem,
        domain=embedding.domain,
        transformation=embedding.transformation,
        constraints=embedding.constraints,
        info_gradient=embedding.info_gradient,
        perspective_name=perspective.name,
        perspective_directive=perspective.directive,
        ground_truth=ground_truth,
    )

    result = await session_manager.submit(prompt, timeout=timeout)
    raw = result.response

    # Parse JSON from response
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            return Projection(
                perspective=data.get("perspective", perspective.name),
                projection=data.get("projection", raw),
                confidence=float(data.get("confidence", 0.5)),
                conflict_points=data.get("conflict_points", []),
                insight_novelty=data.get("insight_novelty", "none extracted"),
                raw_response=raw,
            )
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: wrap the raw response as a projection
    return Projection(
        perspective=perspective.name,
        projection=raw,
        confidence=0.5,
        conflict_points=["JSON parse failed — raw text used"],
        insight_novelty="unable to extract",
        raw_response=raw,
    )


# ---------------------------------------------------------------------------
# Parallel Solver Pool
# ---------------------------------------------------------------------------

async def solve_all(
    problem: str,
    embedding: ConceptualEmbedding,
    perspectives: List[Perspective],
    session_manager,
    timeout: float = 90.0,
) -> List[Projection]:
    """Spawn K independent solver instances in parallel.

    Each instance is strictly isolated — they share the manifold ψ₀ but
    cannot see each other's output.  Uses asyncio.gather for true
    concurrency (bounded by session_manager's rate limiter).
    """
    tasks = [
        _solve_one(problem, embedding, p, session_manager, timeout)
        for p in perspectives
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    projections: List[Projection] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            # Wrap errors as low-confidence fallback projections
            projections.append(Projection(
                perspective=perspectives[i].name,
                projection=f"[SOLVER ERROR: {r}]",
                confidence=0.0,
                conflict_points=[],
                insight_novelty="solver failed",
                raw_response=str(r),
            ))
        else:
            projections.append(r)

    return projections
