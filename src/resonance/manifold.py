"""
R2F Module 1 — Manifold Embedder & Perspective Generator
==========================================================
Takes raw problem P, prompts the LLM for a 4D conceptual embedding ψ₀,
and generates K orthogonal perspectives dynamically from ψ₀.

Output is saved to .state/embedding.json.
Does NOT decompose the problem — only embeds and generates viewpoints.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import STATE_DIR, resolve_model
from src.tools.web_curator import fetch_ground_truth


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ConceptualEmbedding:
    """4D conceptual embedding ψ₀."""
    domain: str           # What field / discipline this problem lives in
    transformation: str   # What change is being requested
    constraints: str      # Hard boundaries and invariants
    info_gradient: str    # Where the biggest uncertainty / knowledge gap is
    raw_text: str = ""    # Full LLM output for traceability

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "transformation": self.transformation,
            "constraints": self.constraints,
            "info_gradient": self.info_gradient,
        }


@dataclass
class Perspective:
    """A single orthogonal perspective for solving the problem."""
    name: str
    directive: str        # System-prompt injection for this perspective
    weight: float = 1.0   # Adaptive weight, updated by recurrence loop

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "directive": self.directive, "weight": self.weight}


# ---------------------------------------------------------------------------
# Default Perspective Bank
# ---------------------------------------------------------------------------

DEFAULT_PERSPECTIVES: List[Dict[str, str]] = [
    {
        "name": "Analytical",
        "directive": (
            "You are a rigorous analyst. Decompose the problem into logical "
            "components. Identify invariants, boundary conditions, and failure "
            "modes. Prove your claims from first principles. No hand-waving."
        ),
    },
    {
        "name": "Empirical",
        "directive": (
            "You are a data-driven empiricist. Cite concrete numbers, real-world "
            "benchmarks, measured latencies, and production incident evidence. "
            "Reject any claim that lacks a measurable basis."
        ),
    },
    {
        "name": "Constructive",
        "directive": (
            "You are a builder. Propose concrete, implementable solutions. "
            "Include code sketches, architecture diagrams in text, specific "
            "library choices, and deployment steps. Be opinionated."
        ),
    },
    {
        "name": "Destructive",
        "directive": (
            "You are a saboteur and red-team specialist. Find every way the "
            "proposed solution can fail, be exploited, or degrade under load. "
            "Assume adversarial inputs and hostile operating conditions."
        ),
    },
    {
        "name": "Analogical",
        "directive": (
            "You are a cross-domain analogist. Find structurally similar problems "
            "in unrelated fields (biology, physics, economics, game theory). "
            "Map their solutions back to this problem. Surprise the reader."
        ),
    },
]


# ---------------------------------------------------------------------------
# Embedding Prompt
# ---------------------------------------------------------------------------

EMBEDDING_PROMPT_TEMPLATE = """Analyze the following problem and extract exactly four conceptual dimensions.
Respond ONLY with valid JSON — no markdown fences, no commentary.

{ground_truth}

Problem: {problem}

Output format:
{{
  "domain": "<primary field/discipline this problem inhabits>",
  "transformation": "<what change or output is being requested>",
  "constraints": "<hard boundaries, invariants, non-negotiables>",
  "info_gradient": "<where the biggest knowledge gap or uncertainty lies>"
}}"""


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

async def embed_problem(
    problem: str,
    session_manager,
    *,
    model_alias: str = "fast",
) -> ConceptualEmbedding:
    """Prompt the LLM for a 4D conceptual embedding of the problem."""

    # Fetch real-time ground truth from SearXNG before embedding
    ground_truth = await fetch_ground_truth(problem[:120], limit=5)
    print(f"  -> Ground Truth fetched ({len(ground_truth)} chars)")

    prompt = EMBEDDING_PROMPT_TEMPLATE.format(problem=problem, ground_truth=ground_truth)
    result = await session_manager.submit(prompt, timeout=60)
    raw = result.response

    # Parse JSON from response (tolerate markdown fences)
    json_str = raw
    json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: create a minimal embedding from the problem itself
        data = {
            "domain": "general",
            "transformation": problem[:100],
            "constraints": "none extracted",
            "info_gradient": "full problem is uncertain",
        }

    return ConceptualEmbedding(
        domain=data.get("domain", "unknown"),
        transformation=data.get("transformation", "unknown"),
        constraints=data.get("constraints", "unknown"),
        info_gradient=data.get("info_gradient", "unknown"),
        raw_text=raw,
    )


def generate_perspectives(
    embedding: ConceptualEmbedding,
    k: int = 5,
) -> List[Perspective]:
    """Generate K orthogonal perspectives, customized to the embedding.

    The base directives are augmented with domain-specific context from ψ₀
    so each perspective is grounded in the problem's actual manifold.
    """
    context_suffix = (
        f"\n\nProblem Domain: {embedding.domain}\n"
        f"Transformation Goal: {embedding.transformation}\n"
        f"Hard Constraints: {embedding.constraints}\n"
        f"Key Uncertainty: {embedding.info_gradient}"
    )

    perspectives: List[Perspective] = []
    for i, spec in enumerate(DEFAULT_PERSPECTIVES[:k]):
        perspectives.append(
            Perspective(
                name=spec["name"],
                directive=spec["directive"] + context_suffix,
                weight=1.0,
            )
        )
    return perspectives


def save_embedding(
    embedding: ConceptualEmbedding,
    perspectives: List[Perspective],
    problem: str,
) -> Path:
    """Persist the embedding and perspectives to .state/embedding.json."""
    payload = {
        "problem": problem,
        "embedding": embedding.to_dict(),
        "perspectives": [p.to_dict() for p in perspectives],
    }
    path = STATE_DIR / "embedding.json"
    path.write_text(json.dumps(payload, indent=2))
    return path
