# Agent Architecture

## Overview

This document describes the architecture of the CLI documentation agent that uses tools (`read_file`, `list_files`) to navigate the project wiki and answer questions.

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

- Positional: The question to ask the agent

**Validation:**

- Checks that a question is provided
- Exits with code 1 if no argument or empty argument

### 3. Tools

The agent has two tools for navigating the project documentation:

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

### 4. Function Calling

Tools are defined as OpenAI-compatible function schemas:

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read the contents of a file...",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Relative path from project root"
        }
      },
      "required": ["path"]
    }
  }
}
```

### 5. Agentic Loop

The agent uses an iterative loop to answer questions:

```
1. Send user question + tool definitions to LLM
2. If LLM returns tool_calls:
   a. Execute each tool
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

1. Use `list_files` to discover relevant files in `wiki/`
2. Use `read_file` to read specific file contents
3. Find answers in the documentation
4. Include source references in the format `path/to/file.md#section-anchor`

## Data Flow

```
┌──────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────┐
│  User    │ ──→ │  agent.py   │ ──→ │  LLM API     │ ──→ │ LLM │
│(question)│     │(agentic loop)│    │(w/ tools)    │     │     │
└──────────┘     └─────────────┘     └──────────────┘     └─────┘
                      │  ▲                                     
                      │  │ tool_calls                          
                      ▼  │                                     
                ┌─────────────┐                                
                │   Tools     │                                
                │ read_file   │                                
                │ list_files  │                                
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
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git workflow\n\n..."
    }
  ]
}
```

**Fields:**

- `answer` (string, required): The agent's final answer
- `source` (string, required): Path to the wiki section with the answer
- `tool_calls` (array, required): All tool invocations with arguments and results

## Error Handling

| Error Type | Handling |
|------------|----------|
| Missing env vars | Print error to stderr, exit code 1 |
| No question provided | Print usage to stderr, exit code 1 |
| HTTP error | Print error + response to stderr, exit code 1 |
| Request error | Print error to stderr, exit code 1 |
| Invalid response | Parse error to stderr, exit code 1 |
| Unsafe path | Return error in tool result, continue loop |
| File not found | Return error in tool result, continue loop |

## Output Rules

- **stdout**: Only valid JSON with `answer`, `source`, and `tool_calls` fields
- **stderr**: All debug/log messages (iteration count, tool calls, etc.)
- **Exit codes**: 0 on success, 1 on any error
- **Max tool calls**: 10 per question

## Dependencies

- `httpx` — HTTP client for API calls
- `python-dotenv` — Environment variable loading

## File Structure

```
.
├── agent.py              # Main agent CLI
├── .env.agent.secret     # LLM configuration
├── AGENT.md              # This documentation
├── plans/
│   ├── task-1.md         # Task 1 plan
│   └── task-2.md         # Task 2 plan
└── wiki/                 # Project documentation
    ├── git.md
    ├── git-workflow.md
    └── ...
```
"# Task 2 Complete"  
