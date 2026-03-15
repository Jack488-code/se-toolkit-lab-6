#!/usr/bin/env python3
"""
CLI agent with tools (read_file, list_files, query_api) and agentic loop.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with fields: answer, source, tool_calls
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Load environment variables from .env.agent.secret
env_path = Path(__file__).parent / ".env.agent.secret"
load_dotenv(env_path)

# Maximum tool calls per question
MAX_TOOL_CALLS = 10


def get_env_vars() -> dict[str, str]:
    """Get required environment variables."""
    # LLM configuration (required)
    llm_required = ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]
    env_vars = {}
    missing = []

    for var in llm_required:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            env_vars[var] = value

    if missing:
        print(f"Error: Missing LLM environment variables: {', '.join(missing)}", file=sys.stderr)
        print(f"Please configure them in {env_path}", file=sys.stderr)
        sys.exit(1)

    # LMS API key (required for query_api)
    lms_api_key = os.getenv("LMS_API_KEY")
    if lms_api_key:
        env_vars["LMS_API_KEY"] = lms_api_key

    # Agent API base URL (optional, default provided)
    agent_api_base = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    env_vars["AGENT_API_BASE_URL"] = agent_api_base

    return env_vars


def is_safe_path(path: str) -> bool:
    """
    Check if a path is safe (within project directory).
    
    Security checks:
    - No path traversal (../)
    - No absolute paths
    - Must be within project root
    """
    # Check for path traversal
    if ".." in path:
        return False
    
    # Check for absolute paths (Unix or Windows)
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        return False
    
    # Resolve the path and ensure it's within project root
    try:
        project_root = Path(__file__).parent.resolve()
        full_path = (project_root / path).resolve()
        # Check if the resolved path is within project root
        return str(full_path).startswith(str(project_root))
    except (ValueError, OSError):
        return False


def read_file(path: str) -> dict[str, Any]:
    """
    Read contents of a file.
    
    Args:
        path: Relative path from project root
        
    Returns:
        Dict with 'success' and 'content' or 'error'
    """
    print(f"read_file: {path}", file=sys.stderr)
    
    if not is_safe_path(path):
        return {"success": False, "error": f"Unsafe path: {path}"}
    
    try:
        project_root = Path(__file__).parent
        full_path = project_root / path
        
        if not full_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        
        if not full_path.is_file():
            return {"success": False, "error": f"Not a file: {path}"}
        
        content = full_path.read_text(encoding="utf-8")
        return {"success": True, "content": content}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(path: str) -> dict[str, Any]:
    """
    List files and directories in a directory.
    
    Args:
        path: Relative path from project root
        
    Returns:
        Dict with 'success' and 'files' list or 'error'
    """
    print(f"list_files: {path}", file=sys.stderr)
    
    if not is_safe_path(path):
        return {"success": False, "error": f"Unsafe path: {path}"}
    
    try:
        project_root = Path(__file__).parent
        full_path = project_root / path
        
        if not full_path.exists():
            return {"success": False, "error": f"Directory not found: {path}"}
        
        if not full_path.is_dir():
            return {"success": False, "error": f"Not a directory: {path}"}
        
        items = []
        for item in full_path.iterdir():
            # Skip hidden files and common ignored directories
            if item.name.startswith(".") and item.name not in [".qwen", ".agents"]:
                continue
            if item.name in ["__pycache__", ".venv", ".git", "node_modules"]:
                continue
            
            suffix = "/" if item.is_dir() else ""
            items.append(f"{item.name}{suffix}")
        
        return {"success": True, "files": sorted(items)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_api(method: str, path: str, body: str | None = None, lms_api_key: str | None = None, api_base_url: str = "http://localhost:42002") -> dict[str, Any]:
    """
    Query the backend LMS API.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g., '/items/', '/analytics/completion-rate')
        body: Optional JSON request body for POST/PUT requests
        lms_api_key: LMS API key for authentication
        api_base_url: Base URL of the API

    Returns:
        Dict with 'success', 'status_code', and 'body' or 'error'
    """
    print(f"query_api: {method} {path}", file=sys.stderr)

    # Validate path (no path traversal)
    if ".." in path:
        return {"success": False, "error": f"Invalid path: {path}"}

    try:
        url = f"{api_base_url}{path}"
        headers = {
            "Content-Type": "application/json",
        }

        # Add authentication header if key is provided
        if lms_api_key:
            headers["Authorization"] = f"Bearer {lms_api_key}"

        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                data = json.loads(body) if body else {}
                response = client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                data = json.loads(body) if body else {}
                response = client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            return {
                "success": True,
                "status_code": response.status_code,
                "body": response.text
            }

    except httpx.HTTPStatusError as e:
        return {
            "success": True,
            "status_code": e.response.status_code,
            "body": e.response.text
        }
    except httpx.RequestError as e:
        return {"success": False, "error": f"Request error: {str(e)}"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON body: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get OpenAI-compatible tool definitions for function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file at the specified path. Use this to read documentation, code, or configuration files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from the project root (e.g., 'wiki/git-workflow.md' or 'README.md')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories in the specified directory. Use this to discover what files exist in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to a directory from the project root (e.g., 'wiki' or 'backend')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Query the backend LMS API to retrieve data or test endpoints. Use this to get current data from the database, check API responses, or test endpoint behavior.",
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
                            "description": "API path (e.g., '/items/', '/analytics/completion-rate', '/api/health')"
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body for POST/PUT requests (e.g., '{\"key\": \"value\"}')"
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


def execute_tool(name: str, args: dict[str, Any], env_vars: dict[str, str] | None = None) -> str:
    """
    Execute a tool and return its result as a string.

    Args:
        name: Tool name (read_file, list_files, or query_api)
        args: Tool arguments
        env_vars: Environment variables (LMS_API_KEY, AGENT_API_BASE_URL)

    Returns:
        String representation of the tool result
    """
    if name == "read_file":
        result = read_file(args.get("path", ""))
        if result["success"]:
            return result["content"]
        else:
            return f"Error: {result['error']}"

    elif name == "list_files":
        result = list_files(args.get("path", ""))
        if result["success"]:
            return "\n".join(result["files"])
        else:
            return f"Error: {result['error']}"

    elif name == "query_api":
        if env_vars is None:
            env_vars = {}
        result = query_api(
            method=args.get("method", "GET"),
            path=args.get("path", ""),
            body=args.get("body"),
            lms_api_key=env_vars.get("LMS_API_KEY"),
            api_base_url=env_vars.get("AGENT_API_BASE_URL", "http://localhost:42002")
        )
        if result["success"]:
            return f"Status: {result['status_code']}\nBody: {result['body']}"
        else:
            return f"Error: {result['error']}"

    else:
        return f"Error: Unknown tool '{name}'"


def call_llm(
    messages: list[dict[str, str]],
    api_key: str,
    api_base: str,
    model: str,
    tools: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """
    Send messages to the LLM API and return the response.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        api_key: LLM API key
        api_base: LLM API base URL
        model: Model name to use
        tools: Optional list of tool definitions for function calling
        
    Returns:
        Dict with 'content' and/or 'tool_calls'
    """
    url = f"{api_base}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    
    if tools:
        payload["tools"] = tools
    
    print(f"Calling LLM API with {len(messages)} messages", file=sys.stderr)
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            message = data["choices"][0]["message"]
            
            result = {
                "content": message.get("content", ""),
                "tool_calls": []
            }
            
            # Parse tool calls if present
            if "tool_calls" in message and message["tool_calls"]:
                for tc in message["tool_calls"]:
                    if tc["type"] == "function":
                        func = tc["function"]
                        try:
                            args = json.loads(func["arguments"])
                        except json.JSONDecodeError:
                            args = {"path": func["arguments"]}
                        
                        result["tool_calls"].append({
                            "id": tc.get("id", f"call_{len(result['tool_calls'])}"),
                            "name": func["name"],
                            "arguments": args
                        })
            
            return result
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Request error: {e}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, IndexError) as e:
        print(f"Error parsing LLM response: {e}", file=sys.stderr)
        sys.exit(1)


def get_system_prompt() -> str:
    """Get the system prompt for the system agent."""
    return """You are a system assistant that helps users with questions about the project. You have access to three tools:

1. `list_files` - List files and directories in a specified directory
2. `read_file` - Read the contents of a file
3. `query_api` - Query the backend LMS API to retrieve data or test endpoints

## When to use each tool:

### Use `read_file` and `list_files` for:
- Documentation questions (wiki/, README.md, etc.)
- Source code analysis
- Configuration files (docker-compose.yml, pyproject.toml, etc.)
- Architecture and design documents

### Use `query_api` for:
- Questions about current data (item counts, scores, etc.)
- Testing API endpoints and checking responses
- HTTP status codes from the API
- Runtime behavior of the system

## Guidelines:

1. For wiki/documentation questions:
   - First use `list_files` to discover relevant files
   - Then use `read_file` to read specific files
   - Find the answer and provide it with a source reference

2. For system/data questions:
   - Use `query_api` with appropriate method and path
   - Interpret the response and provide the answer
   - Source is optional for API queries

3. For source code analysis:
   - Use `read_file` to examine the code
   - Explain findings clearly

For the source field, use the format: `path/to/file.md#section-anchor` or the API endpoint path.
Section anchors are lowercase with hyphens instead of spaces.

Always be thorough. If you don't find the answer, say so clearly."""


def run_agentic_loop(question: str, env_vars: dict[str, str]) -> dict[str, Any]:
    """
    Run the agentic loop to answer a question using tools.
    
    Args:
        question: User's question
        env_vars: Environment variables (LLM_API_KEY, LLM_API_BASE, LLM_MODEL)
        
    Returns:
        Final response with answer, source, and tool_calls
    """
    # Initialize messages with system prompt
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": question}
    ]
    
    # Get tool definitions
    tools = get_tool_definitions()
    
    # Track all tool calls for the final response
    all_tool_calls = []
    
    # Agentic loop
    for iteration in range(MAX_TOOL_CALLS):
        print(f"\n=== Iteration {iteration + 1} ===", file=sys.stderr)
        
        # Call LLM
        response = call_llm(
            messages=messages,
            api_key=env_vars["LLM_API_KEY"],
            api_base=env_vars["LLM_API_BASE"],
            model=env_vars["LLM_MODEL"],
            tools=tools
        )
        
        # Check if LLM returned tool calls
        if response["tool_calls"]:
            print(f"LLM returned {len(response['tool_calls'])} tool call(s)", file=sys.stderr)
            
            # Add assistant message with tool calls (OpenAI format)
            assistant_message = {
                "role": "assistant",
                "content": response["content"],
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"])
                        }
                    }
                    for tc in response["tool_calls"]
                ]
            }
            messages.append(assistant_message)
            
            # Execute each tool call
            for tool_call in response["tool_calls"]:
                tool_name = tool_call["name"]
                tool_args = tool_call["arguments"]

                print(f"Executing tool: {tool_name}({tool_args})", file=sys.stderr)

                # Execute the tool
                tool_result = execute_tool(tool_name, tool_args, env_vars)

                # Record the tool call for final output
                all_tool_calls.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": tool_result
                })

                # Add tool result as a message (OpenAI format)
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_result
                }
                messages.append(tool_message)

            # Continue the loop
            continue
        
        else:
            # LLM returned a final answer (no tool calls)
            print(f"LLM returned final answer", file=sys.stderr)
            
            # Extract source from the response if present
            answer = response["content"]
            source = ""
            
            # Try to find a source reference in the answer
            # Look for patterns like "Source: wiki/file.md" or "See wiki/file.md"
            import re
            source_match = re.search(r'(?:source|see|refer to|from):\s*([^\s\n]+)', answer, re.IGNORECASE)
            if source_match:
                source = source_match.group(1)
            
            # If no source found, try to infer from tool calls
            if not source and all_tool_calls:
                # Use the last read_file path as source
                for tc in reversed(all_tool_calls):
                    if tc["tool"] == "read_file":
                        source = tc["args"].get("path", "")
                        break
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": all_tool_calls
            }
    
    # Max iterations reached
    print(f"Max tool calls ({MAX_TOOL_CALLS}) reached", file=sys.stderr)
    
    # Return whatever we have
    answer = "I reached the maximum number of tool calls. Here's what I found so far."
    source = ""
    
    if all_tool_calls:
        for tc in reversed(all_tool_calls):
            if tc["tool"] == "read_file":
                source = tc["args"].get("path", "")
                break
    
    return {
        "answer": answer,
        "source": source,
        "tool_calls": all_tool_calls
    }


def main() -> None:
    """Main entry point."""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    if not question.strip():
        print("Error: Question cannot be empty", file=sys.stderr)
        sys.exit(1)
    
    # Get environment variables
    env_vars = get_env_vars()
    
    # Run agentic loop
    response = run_agentic_loop(question, env_vars)
    
    # Output JSON response (handle Windows console encoding)
    try:
        print(json.dumps(response, ensure_ascii=False))
    except UnicodeEncodeError:
        # Fallback for Windows console
        print(json.dumps(response, ensure_ascii=True))


if __name__ == "__main__":
    main()
