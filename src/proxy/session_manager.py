"""
Session Proxy Multiplexer — Module 1
=====================================
Headless multi-session manager wrapping Codex CLI via an async subprocess
worker pool.  Includes predictive rate-limiter and token cost estimator.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import (
    AGENTROUTER_API_KEY,
    DEFAULT_MODEL,
    PROJECT_ROOT,
    RATE_LIMIT,
    resolve_model,
)


# ---------------------------------------------------------------------------
# Token Cost Estimator
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token for English text."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Predictive Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Token-bucket rate limiter with concurrency cap."""

    def __init__(
        self,
        max_concurrent: int = RATE_LIMIT.max_concurrent,
        rpm: int = RATE_LIMIT.requests_per_minute,
        cooldown: float = RATE_LIMIT.cooldown_seconds,
    ):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._rpm = rpm
        self._interval = 60.0 / rpm
        self._cooldown = cooldown
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()
        self._total_requests: int = 0
        self._total_tokens_estimate: int = 0
        self._window_start: float = time.monotonic()

    async def acquire(self, estimated_tokens: int = 0) -> None:
        """Wait until we are allowed to send the next request."""
        await self._semaphore.acquire()
        async with self._lock:
            now = time.monotonic()
            elapsed_since_last = now - self._last_request
            if elapsed_since_last < self._interval:
                await asyncio.sleep(self._interval - elapsed_since_last)
            self._last_request = time.monotonic()
            self._total_requests += 1
            self._total_tokens_estimate += estimated_tokens

    def release(self) -> None:
        self._semaphore.release()

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self._total_requests,
            "total_tokens_estimate": self._total_tokens_estimate,
            "elapsed_seconds": round(time.monotonic() - self._window_start, 2),
        }


# ---------------------------------------------------------------------------
# Codex CLI Output Parser
# ---------------------------------------------------------------------------

def _parse_codex_output(raw: str) -> str:
    """Extract the model response from raw Codex exec output."""
    # Find the response block after "codex\n" marker
    parts = raw.split("\ncodex\n")
    if len(parts) >= 2:
        body = parts[1]
        body = re.sub(r"\ntokens used\n[\d,]+\s*$", "", body)
        return body.strip()

    # Fallback: strip header and footer
    lines = raw.strip().splitlines()
    sep_count = 0
    start = 0
    for i, line in enumerate(lines):
        if line.strip() == "--------":
            sep_count += 1
            if sep_count == 1:
                start = i + 1
        if sep_count >= 1 and i > start:
            break
    body = "\n".join(lines[start:])
    body = re.sub(r"\ntokens used\n[\d,]+\s*$", "", body)
    return body.strip()


# ---------------------------------------------------------------------------
# Resolve Codex Binary (prefer local node_modules/.bin/codex)
# ---------------------------------------------------------------------------

def _codex_cmd() -> List[str]:
    """Return the command list for spawning codex.
    
    Prefers the local node_modules/.bin/codex binary (avoids npx startup
    overhead and the 'Need to install?' prompt).
    """
    local_bin = PROJECT_ROOT / "node_modules" / ".bin" / "codex"
    if local_bin.exists():
        return [str(local_bin)]
    # Fallback to npx
    return ["npx", "@openai/codex"]


# ---------------------------------------------------------------------------
# Single-Shot Codex Call
# ---------------------------------------------------------------------------

async def _call_codex(
    prompt: str,
    model: str,
    timeout: float = 60.0,
) -> Tuple[str, float]:
    """Spawn a single Codex exec process and return (response, elapsed_sec).
    
    stdin is connected to /dev/null to prevent Codex from blocking on
    'Reading additional input from stdin...'
    """

    cmd = _codex_cmd() + [
        "exec",
        "-m", model,
        "--skip-git-repo-check",
        prompt,
    ]

    env = {**os.environ, "CODEX_GATEWAY_API_KEY": AGENTROUTER_API_KEY}

    t0 = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,   # <-- critical fix
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd="/tmp",
        env=env,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"Codex timed out after {timeout}s")

    elapsed = time.monotonic() - t0
    raw = stdout.decode("utf-8", errors="replace")

    if proc.returncode != 0 and "codex\n" not in raw:
        err = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Codex exited {proc.returncode}: {err[:500]}"
        )

    return _parse_codex_output(raw), elapsed


# ---------------------------------------------------------------------------
# Session Manager (Process-Pool Orchestrator)
# ---------------------------------------------------------------------------

@dataclass
class SessionResult:
    session_id: str
    model: str
    prompt_hash: str
    response: str
    elapsed_seconds: float
    estimated_tokens: int


class SessionManager:
    """Async multi-session manager with rate-limited Codex CLI calls."""

    def __init__(self, model_alias: str = "primary"):
        self.model = resolve_model(model_alias)
        self.limiter = RateLimiter()
        self._sessions: Dict[str, SessionResult] = {}

    async def submit(
        self,
        prompt: str,
        *,
        model_override: Optional[str] = None,
        timeout: float = 60.0,
    ) -> SessionResult:
        """Submit a single prompt, respecting rate limits."""
        model = model_override or self.model
        est = estimate_tokens(prompt)
        session_id = uuid.uuid4().hex[:12]
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

        await self.limiter.acquire(estimated_tokens=est)
        try:
            response, elapsed = await _call_codex(prompt, model, timeout)
        finally:
            self.limiter.release()

        result = SessionResult(
            session_id=session_id,
            model=model,
            prompt_hash=prompt_hash,
            response=response,
            elapsed_seconds=round(elapsed, 2),
            estimated_tokens=estimate_tokens(response),
        )
        self._sessions[session_id] = result
        return result

    async def submit_batch(
        self,
        prompts: List[str],
        *,
        model_override: Optional[str] = None,
        timeout: float = 60.0,
    ) -> List[SessionResult]:
        """Submit multiple prompts concurrently, governed by rate limits."""
        tasks = [
            self.submit(p, model_override=model_override, timeout=timeout)
            for p in prompts
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "sessions_completed": len(self._sessions),
            "limiter": self.limiter.stats,
        }
