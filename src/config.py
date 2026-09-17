"""
Recurrent-Depth Reasoning Harness — Configuration
===================================================
Environment bindings, model routing dictionary, rate-limiter constants,
and Codex CLI path resolution.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Environment Bindings
# ---------------------------------------------------------------------------

AGENTROUTER_BASE_URL: str = "https://agentrouter.org/v1"
AGENTROUTER_API_KEY: str = os.environ.get("CODEX_GATEWAY_API_KEY", "")

# Anthropic-compatible aliases for transparent proxy
ANTHROPIC_BASE_URL: str = AGENTROUTER_BASE_URL
ANTHROPIC_API_KEY: str = AGENTROUTER_API_KEY


# ---------------------------------------------------------------------------
# Model Routing Dictionary
# ---------------------------------------------------------------------------

MODEL_ROUTES: Dict[str, str] = {
    "claude-opus":       "deepseek-v4-flash",
    "primary":           "deepseek-v4-flash",
    "claude-haiku":      "deepseek-v4-flash",
    "claude-sonnet":     "deepseek-v4-flash",
    "fast":              "deepseek-v4-flash",
    "deepseek-v4-flash": "deepseek-v4-flash",
}

DEFAULT_MODEL: str = "deepseek-v4-flash"


def resolve_model(alias: str) -> str:
    """Resolve a logical alias to the physical AgentRouter model name."""
    return MODEL_ROUTES.get(alias, DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Rate Limiter Constants
# ---------------------------------------------------------------------------

@dataclass
class RateLimitConfig:
    max_concurrent: int = 3
    requests_per_minute: int = 30
    stagger_interval: float = 60.0 / 30
    quota_soft_cap: float = 0.80
    token_budget_per_prompt: int = 4096
    cooldown_seconds: float = 2.0


RATE_LIMIT = RateLimitConfig()


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
STATE_DIR: Path = PROJECT_ROOT / ".state"
STATE_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Codex CLI Resolution
# ---------------------------------------------------------------------------

def codex_binary() -> str:
    which = shutil.which("codex")
    if which:
        return which
    return "npx"


def codex_cmd_prefix() -> list[str]:
    binary = codex_binary()
    if binary == "npx":
        return ["npx", "@openai/codex"]
    return [binary]
