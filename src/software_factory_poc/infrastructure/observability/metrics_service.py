"""Prometheus metrics declarations for BrahMAS.

All metrics are declared statically at module level.
Labels use ONLY static enumerations — never dynamic IDs (UUIDs, issue keys, hashes).
"""

from prometheus_client import Counter, Gauge, Histogram

# ── Mission-level metrics ──────────────────────────────────────────

MISSIONS_TOTAL = Counter(
    "brahmas_missions_total",
    "Total completed missions",
    ["agent", "flow_mode", "outcome"],
)

MISSION_DURATION_SECONDS = Histogram(
    "brahmas_mission_duration_seconds",
    "End-to-end mission duration in seconds",
    ["agent", "flow_mode"],
)

MISSIONS_INFLIGHT = Gauge(
    "brahmas_missions_inflight",
    "Currently running missions",
    ["agent"],
)

# ── MCP tool call metrics ─────────────────────────────────────────

MCP_CALLS_TOTAL = Counter(
    "brahmas_mcp_calls_total",
    "Total MCP tool invocations",
    ["provider", "tool", "outcome"],
)

# ── LLM metrics ───────────────────────────────────────────────────

LLM_TOKENS_TOTAL = Counter(
    "brahmas_llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "type"],
)

LLM_LATENCY_SECONDS = Histogram(
    "brahmas_llm_latency_seconds",
    "LLM inference latency in seconds",
    ["model"],
)
