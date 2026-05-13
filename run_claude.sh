#!/usr/bin/env bash

# Anthropic-compatible local backend
export ANTHROPIC_BASE_URL=http://agentserver.tailda962e.ts.net:8080
export ANTHROPIC_AUTH_TOKEN=dummy

# Model: one local model mapped to all Claude Code tiers
MODEL=Qwen3.6-35B-A3B

# Force active model for this session
export ANTHROPIC_MODEL=$MODEL

# Map Claude Code aliases to your local model
export ANTHROPIC_DEFAULT_HAIKU_MODEL=$MODEL
export ANTHROPIC_DEFAULT_SONNET_MODEL=$MODEL
export ANTHROPIC_DEFAULT_OPUS_MODEL=$MODEL
export CLAUDE_CODE_SUBAGENT_MODEL=$MODEL

# Optional: make it appear nicely in /model
export ANTHROPIC_CUSTOM_MODEL_OPTION=$MODEL
export ANTHROPIC_CUSTOM_MODEL_OPTION_NAME="Qwen3.6 35B A3B"
export ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION="Local Qwen3.6-35B-A3B via Anthropic-compatible backend"

# Auto-compact around 32k tokens
unset DISABLE_COMPACT
unset DISABLE_AUTO_COMPACT

export CLAUDE_CODE_AUTO_COMPACT_WINDOW=65536
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=90

# Output cap
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=8192

# Precision sampling for Qwen
export CLAUDE_CODE_EXTRA_BODY='{
  "temperature": 0.15,
  "top_p": 0.85,
  "top_k": 20,
  "min_p": 0.0
}'

# Local-backend compatibility
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
export CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1
export CLAUDE_CODE_ATTRIBUTION_HEADER=0

unset MAX_THINKING_TOKENS

# Keep traffic local / private
export DISABLE_TELEMETRY=1
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1


unset CLAUDE_CODE_DISABLE_THINKING

# Optional: longer timeout for slow local inference
export API_TIMEOUT_MS=1800000   # 30 min
CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=1

# Start Claude Code
claude