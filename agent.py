#!/usr/bin/env python3
"""
CLI agent that sends questions to an LLM and returns structured JSON response.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with fields: answer, tool_calls
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables from .env.agent.secret
env_path = Path(__file__).parent / ".env.agent.secret"
load_dotenv(env_path)


def get_env_vars() -> dict[str, str]:
    """Get required environment variables."""
    required = ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]
    env_vars = {}
    missing = []
    
    for var in required:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            env_vars[var] = value
    
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print(f"Please configure them in {env_path}", file=sys.stderr)
        sys.exit(1)
    
    return env_vars


def call_lllm(question: str, api_key: str, api_base: str, model: str) -> str:
    """
    Send a question to the LLM API and return the answer.
    
    Args:
        question: The user's question
        api_key: LLM API key
        api_base: LLM API base URL
        model: Model name to use
    
    Returns:
        The LLM's text response
    """
    url = f"{api_base}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": question}
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    
    print(f"Sending request to LLM: {question}", file=sys.stderr)
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            
            print(f"Received response from LLM", file=sys.stderr)
            return answer
            
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
    
    # Call LLM
    answer = call_lllm(
        question=question,
        api_key=env_vars["LLM_API_KEY"],
        api_base=env_vars["LLM_API_BASE"],
        model=env_vars["LLM_MODEL"],
    )
    
    # Output JSON response
    response = {
        "answer": answer,
        "tool_calls": [],
    }
    
    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
