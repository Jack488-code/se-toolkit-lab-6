"""Regression tests for agent.py CLI.

These tests verify that agent.py:
- Returns valid JSON output
- Has required fields (answer, tool_calls)
- Exits with code 0 on success
"""

import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).parent.parent.parent.parent
AGENT_PATH = ROOT_DIR / "agent.py"
ENV_FILE = ROOT_DIR / ".env.agent.secret"


def test_agent_returns_valid_json():
    """Test that agent.py returns valid JSON with required fields.
    
    This test verifies the basic contract of the agent:
    - It accepts a question as a command-line argument
    - It outputs valid JSON to stdout
    - The JSON has 'answer' and 'tool_calls' fields
    """
    # Check that .env.agent.secret exists
    if not ENV_FILE.exists():
        raise RuntimeError(
            f"{ENV_FILE} not found. "
            "Copy .env.agent.example to .env.agent.secret and configure your LLM API credentials."
        )
    
    # Run agent.py with a simple test question
    result = subprocess.run(
        [sys.executable, str(AGENT_PATH), "What is 2 + 2?"],
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
    )
    
    # Check exit code
    assert result.returncode == 0, f"agent.py failed with exit code {result.returncode}\nstderr: {result.stderr}"
    
    # Check that stdout is valid JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"agent.py output is not valid JSON: {e}\nstdout: {result.stdout}")
    
    # Check required fields
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    
    # Check field types
    assert isinstance(output["answer"], str), "'answer' should be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' should be a list"
    
    # Check that answer is not empty
    assert len(output["answer"].strip()) > 0, "'answer' field is empty"


def test_agent_missing_question_exits_with_error():
    """Test that agent.py exits with error when no question is provided."""
    result = subprocess.run(
        [sys.executable, str(AGENT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
    )
    
    # Should exit with non-zero code
    assert result.returncode != 0, "agent.py should exit with error when no question provided"
    
    # Should print usage to stderr
    assert "Usage" in result.stderr or "usage" in result.stderr, \
        "agent.py should print usage message to stderr when no question provided"
