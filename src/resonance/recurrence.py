"""
R2F Module 4 — Recurrence, Tunneling, and Reinjection (Layer 4 & 5)
=====================================================================
Generates the next prompt by reinjecting the dominant eigenstate back to
the K instances. If E is stuck (stable but < 0.8), inject semantic noise
(Quantum Tunneling) to force a perspective shift.
"""

import random

TUNNELING_NOISE = [
    "COUNTER-FACTUAL INJECTION: What if the primary constraint we assumed is actually a symptom of a deeper bottleneck? Reverse the dependency.",
    "TEMPERATURE SPIKE: Assume the current consensus is fundamentally naive. Propose a solution that would have been fired for being too radical 5 years ago.",
    "DIMENSIONAL COLLAPSE: What if we remove the most expensive component entirely? How does the system survive?",
    "ADVERSARIAL PERTURBATION: An adversary knows this exact plan and is exploiting its blind spots. Where are they attacking?"
]

REINJECTION_PROMPT_TEMPLATE = """You are continuing a multi-perspective resonance session.

PROBLEM:
{problem}

YOUR ASSIGNED PERSPECTIVE: {perspective_name}
(Remember to stay absolutely committed to this angle.)

{dominant_state_str}

=== ITERATION INSTRUCTIONS ===
The system has computed the overlap and stability of all viewpoints. The state above represents the current dominant consensus (Eigenstate). 

Your task: Evaluate this dominant state strictly from your {perspective_name} angle.
1. Does it violate your core principles? If so, attack it.
2. Does it align with your angle? If so, strengthen it with deeper specifics.

{tunneling_injection}

Respond ONLY with valid JSON:
{{
  "perspective": "{perspective_name}",
  "projection": "<your refined analysis taking the consensus into account>",
  "confidence": <float 0.0-1.0>,
  "conflict_points": ["..."],
  "insight_novelty": "..."
}}"""


def generate_reinjection_prompt(
    problem: str,
    perspective_name: str,
    dominant_state_str: str,
    E_dom: float,
    iteration: int,
) -> str:
    """Format the prompt for the next recurrence loop iteration."""

    tunneling_injection = ""
    # Quantum Tunneling (Anti-Stuck Protocol)
    # If stability is moderate (E between 0.5 and 0.8) and we are past iteration 1
    if 0.5 < E_dom < 0.8 and iteration > 0:
        noise = random.choice(TUNNELING_NOISE)
        tunneling_injection = f"*** QUANTUM TUNNELING TRIGGERED ***\n{noise}\n"

    return REINJECTION_PROMPT_TEMPLATE.format(
        problem=problem,
        perspective_name=perspective_name,
        dominant_state_str=dominant_state_str,
        tunneling_injection=tunneling_injection,
    )
