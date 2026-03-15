# Agent Architecture

## Overview

This document describes the architecture of the CLI system agent that uses tools (`read_file`, `list_files`, `query_api`) to answer questions about the project documentation, source code, and running system.

## Components

### 1. Environment Configuration

The agent loads configuration from environment variables:

**From `.env.agent.secret`:**

- `LLM_API_KEY` — API key for the LLM provider
- `LLM_API_BASE` — Base URL of the LLM API (OpenAI-compatible endpoint)
- `LLM_MODEL` — Model name to use for completions

**From `.env.docker.secret` or environment:**

- `LMS_API_KEY` — Backend API key for `query_api` authentication
- `AGENT_API_BASE_URL` — Base URL for the backend API (default: `http://localhost:42002`)

Uses `python-dotenv` to load environment variables from `.env` files.

### 2. CLI Interface

**Entry point:** `agent.py`

**Usage:**

```bash
uv run agent.py "Your question here"
```

**Arguments:**

- Positional: The question to ask the agent

**Validation:**

- Checks that a question is provided
- Exits with code 1 if no argument or empty argument

### 3. Tools

The agent has three tools for interacting with the project:

#### read_file

- **Purpose:** Read contents of a file at the specified path
- **Parameters:** `path` (string) — relative path from project root
- **Returns:** File contents as string, or error message
- **Security:** Blocks path traversal (`../`) and absolute paths

#### list_files

- **Purpose:** List files and directories in a specified directory
- **Parameters:** `path` (string) — relative path to directory from project root
- **Returns:** Newline-separated list of files/directories
- **Security:** Blocks path traversal (`../`) and absolute paths

#### query_api

- **Purpose:** Query the backend LMS API to retrieve data or test endpoints
- **Parameters:**
  - `method` (string) — HTTP method (GET, POST, PUT, DELETE)
  - `path` (string) — API path (e.g., `/items/`, `/analytics/completion-rate`)
  - `body` (string, optional) — JSON request body for POST/PUT requests
- **Returns:** HTTP status code and response body
- **Authentication:** Uses `LMS_API_KEY` from environment variables
- **Security:** Validates path to prevent path traversal

### 4. Function Calling

Tools are defined as OpenAI-compatible function schemas:

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Query the backend LMS API to retrieve data or test endpoints...",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method (GET, POST, PUT, DELETE)",
          "enum": ["GET", "POST", "PUT", "DELETE"]
        },
        "path": {
          "type": "string",
          "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

### 5. Agentic Loop

The agent uses an iterative loop to answer questions:

```
1. Send user question + tool definitions to LLM
2. If LLM returns tool_calls:
   a. Execute each tool with appropriate parameters
   b. Add tool results as "tool" role messages
   c. Repeat from step 1
3. If LLM returns text answer (no tool_calls):
   a. Extract answer and source
   b. Output JSON and exit
4. Max 10 tool calls per question
```

### 6. LLM Client

**Function:** `call_llm(messages, api_key, api_base, model, tools)`

Makes an HTTP POST request to `{api_base}/chat/completions` with:

- Messages array (system, user, assistant, tool roles)
- Optional tool definitions for function calling

**Headers:**

- `Authorization: Bearer <api_key>`
- `Content-Type: application/json`

**Timeout:** 60 seconds

### 7. System Prompt

The system prompt instructs the LLM to:

1. Use `read_file` and `list_files` for:
   - Documentation questions (wiki/, README.md, etc.)
   - Source code analysis
   - Configuration files

2. Use `query_api` for:
   - Questions about current data (item counts, scores, etc.)
   - Testing API endpoints and checking responses
   - HTTP status codes from the API
   - Runtime behavior of the system

3. Provide source references in the format: `path/to/file.md#section-anchor` or API endpoint path

## Tool Selection Strategy

| Question Type | Use |
|--------------|-----|
| Wiki/Documentation | `read_file`, `list_files` |
| Source code | `read_file` |
| Configuration files | `read_file` |
| Current data | `query_api` |
| API behavior | `query_api` |
| System architecture | `read_file` (docker-compose.yml, etc.) |

## Data Flow

```
┌──────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────┐
│  User    │ ──→ │  agent.py   │ ──→ │  LLM API     │ ──→ │ LLM │
│(question)│     │(agentic loop)│    │(w/ 3 tools)  │     │     │
└──────────┘     └─────────────┘     └──────────────┘     └─────┘
                      │  ▲                                     
                      │  │ tool_calls                          
                      ▼  │                                     
                ┌─────────────┐                                
                │   Tools     │                                
                │ read_file   │                                
                │ list_files  │                                
                │ query_api   │                                
                └─────────────┘                                
                      │                                        
                      ▼                                        
                ┌───────────┐                                  
                │ JSON out  │                                  
                │ (stdout)  │                                  
                └───────────┘                                  
```

## Security

| Threat | Mitigation |
|--------|------------|
| Path traversal (`../`) | Reject paths containing `..` |
| Absolute paths | Reject paths starting with `/` or drive letter |
| Symlinks outside project | Resolve paths and verify they're within project root |
| Hardcoded API keys | Read all secrets from environment variables |
| Unauthorized API access | Always include `LMS_API_KEY` header in `query_api` |

## Output Format

```json
{
  "answer": "The agent's answer to the question",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\ngit.md\n..."
    },
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "Status: 200\nBody: [...]"
    }
  ]
}
```

**Fields:**

- `answer` (string, required): The agent's final answer
- `source` (string, optional): Path to the wiki section or API endpoint
- `tool_calls` (array, required): All tool invocations with arguments and results

## Error Handling

| Error Type | Handling |
|------------|----------|
| Missing LLM env vars | Print error to stderr, exit code 1 |
| No question provided | Print usage to stderr, exit code 1 |
| HTTP error (LLM) | Print error + response to stderr, exit code 1 |
| Request error | Print error to stderr, exit code 1 |
| Invalid response | Parse error to stderr, exit code 1 |
| Unsafe path | Return error in tool result, continue loop |
| File not found | Return error in tool result, continue loop |
| API unavailable | Return error in tool result, continue loop |

## Output Rules

- **stdout**: Only valid JSON with `answer`, `source`, and `tool_calls` fields
- **stderr**: All debug/log messages (iteration count, tool calls, etc.)
- **Exit codes**: 0 on success, 1 on any error
- **Max tool calls**: 10 per question

## Dependencies

- `httpx` — HTTP client for API calls (LLM and backend)
- `python-dotenv` — Environment variable loading

## File Structure

```
.
├── agent.py              # Main agent CLI
├── .env.agent.secret     # LLM configuration
├── .env.docker.secret    # Backend API configuration
├── AGENT.md              # This documentation
├── plans/
│   ├── task-1.md         # Task 1 plan
│   ├── task-2.md         # Task 2 plan
│   └── task-3.md         # Task 3 plan
├── test_agent.py         # Regression tests
├── wiki/                 # Project documentation
│   ├── git.md
│   ├── git-workflow.md
│   └── ...
└── backend/              # Backend source code
    ├── app/
    └── ...
```

## Benchmark Results

### Initial Run

- Score: TBD/10
- Failed questions: TBD

### Iterations

1. **Iteration 1:** Baseline score
2. **Iteration 2:** Fixed tool descriptions
3. **Iteration 3:** Improved system prompt
4. **Iteration 4:** Edge cases

### Final Score

- **Score:** TBD/10 (pending autochecker)

## Lessons Learned

1. **Tool descriptions matter:** Clear, specific descriptions help the LLM choose the right tool.

2. **Environment variables are critical:** Never hardcode API keys or URLs. The autochecker injects its own values.

3. **System prompt guides behavior:** Explicit instructions about when to use each tool improves accuracy.

4. **Error handling in tools:** Returning errors as tool results (not exceptions) allows the LLM to recover.

5. **Max iterations:** 10 tool calls is usually enough, but complex questions may need more.
