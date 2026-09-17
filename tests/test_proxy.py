"""
Tests for Module 1 — Session Proxy Multiplexer
===============================================
Verifies:
  1. Config model routing resolves correctly.
  2. Token estimator produces sane values.
  3. Rate limiter enforces stagger intervals and concurrency caps.
  4. Codex output parser extracts clean responses.
  5. (Live) Single-shot Codex call via AgentRouter.
  6. (Live) Concurrent batch calls respect rate limits.
"""

import asyncio
import os
import sys
import time

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import resolve_model, RATE_LIMIT, DEFAULT_MODEL
from src.proxy.session_manager import (
    RateLimiter,
    SessionManager,
    _parse_codex_output,
    estimate_tokens,
)

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"


# ---------------------------------------------------------------------------
# Test 1: Model Routing
# ---------------------------------------------------------------------------

def test_model_routing():
    assert resolve_model("claude-opus") == "deepseek-v4-flash"
    assert resolve_model("primary") == "deepseek-v4-flash"
    assert resolve_model("claude-haiku") == "deepseek-v4-flash"
    assert resolve_model("unknown-xyz") == DEFAULT_MODEL
    print(f"  {PASS}  test_model_routing")


# ---------------------------------------------------------------------------
# Test 2: Token Estimator
# ---------------------------------------------------------------------------

def test_token_estimator():
    assert estimate_tokens("") == 1  # min clamp
    assert estimate_tokens("hello world") == max(1, len("hello world") // 4)
    long_text = "a" * 4000
    assert 900 <= estimate_tokens(long_text) <= 1100
    print(f"  {PASS}  test_token_estimator")


# ---------------------------------------------------------------------------
# Test 3: Rate Limiter — Stagger Enforcement
# ---------------------------------------------------------------------------

async def test_rate_limiter_stagger():
    """Three rapid acquires should be staggered by at least the interval."""
    limiter = RateLimiter(max_concurrent=3, rpm=30, cooldown=0)
    t0 = time.monotonic()

    timestamps = []
    for _ in range(3):
        await limiter.acquire(estimated_tokens=100)
        timestamps.append(time.monotonic())
        limiter.release()

    # Gap between first and third should be >= 2 * interval (≈ 4 sec)
    gap = timestamps[2] - timestamps[0]
    expected_min = 2 * (60.0 / 30) * 0.8  # 80 % tolerance
    assert gap >= expected_min, f"gap {gap:.2f}s < expected {expected_min:.2f}s"
    print(f"  {PASS}  test_rate_limiter_stagger (gap={gap:.2f}s)")


# ---------------------------------------------------------------------------
# Test 4: Rate Limiter — Concurrency Cap
# ---------------------------------------------------------------------------

async def test_rate_limiter_concurrency():
    """More tasks than max_concurrent should queue, not run in parallel."""
    limiter = RateLimiter(max_concurrent=2, rpm=600, cooldown=0)
    active = 0
    max_active = 0

    async def worker():
        nonlocal active, max_active
        await limiter.acquire()
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.1)
        active -= 1
        limiter.release()

    await asyncio.gather(*[worker() for _ in range(5)])
    assert max_active <= 2, f"max_active={max_active}, expected <=2"
    print(f"  {PASS}  test_rate_limiter_concurrency (max_active={max_active})")


# ---------------------------------------------------------------------------
# Test 5: Output Parser
# ---------------------------------------------------------------------------

def test_output_parser():
    raw = (
        "OpenAI Codex v0.154.0\n"
        "--------\n"
        "workdir: /tmp\n"
        "model: deepseek-v4-flash\n"
        "--------\n"
        "user\n"
        "Say Apple\n"
        "codex\n"
        "Apple.\n"
        "tokens used\n"
        "1,075\n"
    )
    parsed = _parse_codex_output(raw)
    assert parsed == "Apple.", f"Got: {parsed!r}"
    print(f"  {PASS}  test_output_parser")

    # Test with multi-line response
    raw2 = (
        "OpenAI Codex v0.154.0\n"
        "--------\n"
        "workdir: /tmp\n"
        "--------\n"
        "user\n"
        "Explain X\n"
        "codex\n"
        "Line one.\n"
        "Line two.\n"
        "Line three.\n"
        "tokens used\n"
        "2,500\n"
    )
    parsed2 = _parse_codex_output(raw2)
    assert "Line one." in parsed2
    assert "Line three." in parsed2
    assert "tokens used" not in parsed2
    print(f"  {PASS}  test_output_parser_multiline")


# ---------------------------------------------------------------------------
# Test 6: Live Single-Shot Call
# ---------------------------------------------------------------------------

async def test_live_single_call():
    """Actually call Codex via AgentRouter. Requires network + valid key."""
    mgr = SessionManager(model_alias="fast")
    result = await mgr.submit("Respond with only the word 'Pineapple'.", timeout=30)
    assert len(result.response) > 0, "Empty response"
    assert result.elapsed_seconds > 0
    print(f"  {PASS}  test_live_single_call (model={result.model}, "
          f"elapsed={result.elapsed_seconds}s, tokens~{result.estimated_tokens})")
    print(f"         Response: {result.response[:80]!r}")


# ---------------------------------------------------------------------------
# Test 7: Live Concurrent Batch (Rate-Limited)
# ---------------------------------------------------------------------------

async def test_live_batch_rate_limited():
    """Submit 3 prompts concurrently; verify they complete and limiter stats."""
    mgr = SessionManager(model_alias="fast")
    prompts = [
        "Respond with only the word 'Red'.",
        "Respond with only the word 'Blue'.",
        "Respond with only the word 'Green'.",
    ]
    results = await mgr.submit_batch(prompts, timeout=60)
    assert len(results) == 3
    for r in results:
        assert len(r.response) > 0
    stats = mgr.stats
    assert stats["sessions_completed"] == 3
    print(f"  {PASS}  test_live_batch_rate_limited")
    print(f"         Stats: {stats}")
    for r in results:
        print(f"         [{r.session_id}] {r.response[:40]!r} ({r.elapsed_seconds}s)")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def main():
    print("\n=== Module 1 — Proxy & Session Manager Tests ===\n")

    # Unit tests (no network)
    test_model_routing()
    test_token_estimator()
    test_output_parser()
    await test_rate_limiter_stagger()
    await test_rate_limiter_concurrency()

    # Live tests (require network + valid API key)
    print("\n--- Live Integration Tests ---\n")
    await test_live_single_call()
    await test_live_batch_rate_limited()

    print("\n=== All Module 1 Tests Passed ===\n")


if __name__ == "__main__":
    asyncio.run(main())
