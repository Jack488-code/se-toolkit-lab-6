# Agent Architecture

## Overview

This document describes the architecture of the CLI agent that sends questions to an LLM and returns structured JSON responses.

## Components

### 1. Environment Configuration

The agent loads configuration from `.env.agent.secret`:

- `LLM_API_KEY` — API key for the LLM provider
- `LLM_API_BASE` — Base URL of the LLM API (OpenAI-compatible endpoint)
- `LLM_MODEL` — Model name to use for completions

Uses `python-dotenv` to load environment variables from the `.env` file.

### 2. CLI Interface

**Entry point:** `agent.py`

**Usage:**
```bash
uv run agent.py "Your question here"
```

**Arguments:**
- Positional: The question to ask the LLM

**Validation:**
- Checks that a question is provided
- Exits with code 1 if no argument or empty argument

### 3. LLM Client

**Function:** `call_llm(question, api_key, api_base, model)`

Makes an HTTP POST request to `{api_base}/chat/completions` with:

```json
{
  "model": "<model_name>",
  "messages": [{"role": "user", "content": "<question>"}],
  "temperature": 0.7,
  "max_tokens": 1024
}
```

**Headers:**
- `Authorization: Bearer <api_key>`
- `Content-Type: application/json`

**Timeout:** 60 seconds

### 4. Response Handler

Parses the LLM response and extracts the answer from:
```
response["choices"][0]["message"]["content"]
```

Outputs JSON to stdout:
```json
{
  "answer": "<LLM response text>",
  "tool_calls": []
}
```

## Data Flow

```
┌──────────┐     ┌───────────┐     ┌─────────────┐     ┌─────┐
│  User    │ ──→ │ agent.py  │ ──→ │ LLM API     │ ──→ │ LLM │
│ (CLI arg)│     │ (CLI)     │     │ (HTTP POST) │     │     │
└──────────┘     └───────────┘     └─────────────┘     └─────┘
                                            │
                                            ▼
                                     ┌───────────┐
                                     │ JSON out  │
                                     │ (stdout)  │
                                     └───────────┘
```

## Error Handling

| Error Type | Handling |
|------------|----------|
| Missing env vars | Print error to stderr, exit code 1 |
| No question provided | Print usage to stderr, exit code 1 |
| HTTP error | Print error + response to stderr, exit code 1 |
| Request error | Print error to stderr, exit code 1 |
| Invalid response | Parse error to stderr, exit code 1 |

## Output Rules

- **stdout**: Only valid JSON with `answer` and `tool_calls` fields
- **stderr**: All debug/log messages
- **Exit codes**: 0 on success, 1 on any error

## Dependencies

- `httpx` — HTTP client for API calls
- `python-dotenv` — Environment variable loading

## Future Extensions (Tasks 2-3)

- Tool system: `tool_calls` array will be populated with tool invocations
- Agent loop: Iterative reasoning with tool usage
- Additional tools: `read_file`, `list_files`, `query_api`, etc.
