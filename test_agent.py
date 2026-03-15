"""Regression tests for agent.py CLI.

These tests verify that agent.py:
- Returns valid JSON output
- Has required fields (answer, source, tool_calls)
- Uses tools correctly (read_file, list_files)
- Exits with code 0 on success
"""

import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).parent
AGENT_PATH = ROOT_DIR / "agent.py"
ENV_FILE = ROOT_DIR / ".env.agent.secret"


def run_agent(question: str) -> tuple[int, dict, str]:
    """Run agent.py with a question and return exit code, output, stderr."""
    result = subprocess.run(
        [sys.executable, str(AGENT_PATH), question],
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
        timeout=120,
    )
    
    output = {}
    if result.stdout.strip():
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    
    return result.returncode, output, result.stderr


def test_agent_returns_valid_json():
    """Test that agent.py returns valid JSON with required fields."""
    if not ENV_FILE.exists():
        raise RuntimeError(
            f"{ENV_FILE} not found. "
            "Copy .env.agent.example to .env.agent.secret and configure your LLM API credentials."
        )
    
    returncode, output, stderr = run_agent("What is 2 + 2?")
    
    assert returncode == 0, f"agent.py failed with exit code {returncode}\nstderr: {stderr}"
    assert "answer" in output, "Missing 'answer' field in output"
    assert "source" in output, "Missing 'source' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["answer"], str), "'answer' should be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' should be a list"


def test_agent_missing_question_exits_with_error():
    """Test that agent.py exits with error when no question is provided."""
    result = subprocess.run(
        [sys.executable, str(AGENT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
    )
    
    assert result.returncode != 0, "agent.py should exit with error when no question provided"
    assert "Usage" in result.stderr or "usage" in result.stderr, \
        "agent.py should print usage message to stderr when no question provided"


def test_agent_uses_list_files_for_wiki_question():
    """Test that agent.py uses list_files tool when asked about wiki files.
    
    Question: "What files are in the wiki directory?"
    Expected: list_files tool is called with path "wiki"
    """
    if not ENV_FILE.exists():
        raise RuntimeError(
            f"{ENV_FILE} not found. "
            "Copy .env.agent.example to .env.agent.secret and configure your LLM API credentials."
        )
    
    returncode, output, stderr = run_agent("What files are in the wiki directory?")
    
    assert returncode == 0, f"agent.py failed with exit code {returncode}\nstderr: {stderr}"
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert len(output["tool_calls"]) > 0, "Expected at least one tool call"
    
    # Check that list_files was called
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "list_files" in tool_names, f"Expected list_files tool call, got: {tool_names}"
    
    # Check that list_files was called with wiki path
    list_files_calls = [tc for tc in output["tool_calls"] if tc.get("tool") == "list_files"]
    wiki_paths = [tc.get("args", {}).get("path") for tc in list_files_calls]
    assert any("wiki" in str(p) for p in wiki_paths), \
        f"Expected list_files to be called with wiki path, got: {wiki_paths}"


def test_agent_uses_read_file_for_merge_conflict_question():
    """Test that agent.py uses read_file tool when asked about merge conflicts.
    
    Question: "How do you resolve a merge conflict?"
    Expected: read_file tool is called, source contains git-related wiki file
    """
    if not ENV_FILE.exists():
        raise RuntimeError(
            f"{ENV_FILE} not found. "
            "Copy .env.agent.example to .env.agent.secret and configure your LLM API credentials."
        )
    
    returncode, output, stderr = run_agent("How do you resolve a merge conflict?")
    
    assert returncode == 0, f"agent.py failed with exit code {returncode}\nstderr: {stderr}"
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert len(output["tool_calls"]) > 0, "Expected at least one tool call"
    
    # Check that read_file was called
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "read_file" in tool_names, f"Expected read_file tool call, got: {tool_names}"
    
    # Check that source contains git-related wiki file
    source = output.get("source", "")
    assert "git" in source.lower(), f"Expected source to contain git-related file, got: {source}"
    
    # Check that read_file was called with git-related file
    read_file_calls = [tc for tc in output["tool_calls"] if tc.get("tool") == "read_file"]
    git_files = [tc.get("args", {}).get("path") for tc in read_file_calls if "git" in tc.get("args", {}).get("path", "").lower()]
    assert len(git_files) > 0, f"Expected read_file to be called with git-related file, got: {[tc.get('args') for tc in read_file_calls]}"


def test_agent_uses_read_file_for_framework_question():
    """Test that agent.py uses read_file tool when asked about the backend framework.

    Question: "What Python web framework does the backend use?"
    Expected: read_file tool is called to examine source code or configuration
    """
    if not ENV_FILE.exists():
        raise RuntimeError(
            f"{ENV_FILE} not found. "
            "Copy .env.agent.example to .env.agent.secret and configure your LLM API credentials."
        )

    returncode, output, stderr = run_agent("What Python web framework does the backend use?")

    assert returncode == 0, f"agent.py failed with exit code {returncode}\nstderr: {stderr}"
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert len(output["tool_calls"]) > 0, "Expected at least one tool call"

    # Check that read_file was called
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "read_file" in tool_names, f"Expected read_file tool call, got: {tool_names}"


def test_agent_uses_query_api_for_data_question():
    """Test that agent.py uses query_api tool when asked about database data.

    Question: "How many items are in the database?"
    Expected: query_api tool is called with GET /items/
    """
    if not ENV_FILE.exists():
        raise RuntimeError(
            f"{ENV_FILE} not found. "
            "Copy .env.agent.example to .env.agent.secret and configure your LLM API credentials."
        )

    returncode, output, stderr = run_agent("How many items are in the database?")

    assert returncode == 0, f"agent.py failed with exit code {returncode}\nstderr: {stderr}"
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert len(output["tool_calls"]) > 0, "Expected at least one tool call"

    # Check that query_api was called
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "query_api" in tool_names, f"Expected query_api tool call, got: {tool_names}"

    # Check that query_api was called with GET method and items path
    query_api_calls = [tc for tc in output["tool_calls"] if tc.get("tool") == "query_api"]
    assert len(query_api_calls) > 0, "Expected at least one query_api call"

    # Check method and path
    methods = [tc.get("args", {}).get("method") for tc in query_api_calls]
    paths = [tc.get("args", {}).get("path") for tc in query_api_calls]
    assert any("GET" in str(m).upper() for m in methods), f"Expected GET method, got: {methods}"
    assert any("items" in str(p).lower() for p in paths), f"Expected items path, got: {paths}"
