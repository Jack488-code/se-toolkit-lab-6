# Task 3 Plan: The System Agent

## Overview
Добавить инструмент `query_api` для взаимодействия с backend API и обновить агента для ответа на вопросы о системе и данных.

## Architecture

### New Tool: query_api

**Schema:**
```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Query the backend LMS API to retrieve data or test endpoints",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method (GET, POST, etc.)",
          "enum": ["GET", "POST", "PUT", "DELETE"]
        },
        "path": {
          "type": "string",
          "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body for POST/PUT requests"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

**Implementation:**
- Использует `httpx` для HTTP запросов
- Добавляет `Authorization: Bearer <LMS_API_KEY>` header
- Base URL из `AGENT_API_BASE_URL` (default: `http://localhost:42002`)
- Возвращает JSON string с `status_code` и `body`

### Environment Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider API key |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | Env (optional) | Backend base URL (default: http://localhost:42002) |

### System Prompt Updates

The system prompt should instruct the LLM to:
1. Use `query_api` for questions about:
   - Current data (item counts, scores)
   - API behavior (status codes, errors)
   - System configuration
2. Use `read_file`/`list_files` for:
   - Documentation questions
   - Source code analysis
   - Configuration files
3. Combine tools when needed (e.g., query API → get error → read source code)

### Tool Selection Strategy

```
Question about... → Use...
- Wiki/Documentation → read_file, list_files
- Current data → query_api
- API behavior → query_api
- Source code → read_file
- System architecture → read_file (docker-compose.yml, etc.)
```

## Security

| Threat | Mitigation |
|--------|------------|
| Hardcoded API keys | Read from environment variables only |
| Path traversal in API | Validate path doesn't contain `..` |
| Unauthorized API access | Always include LMS_API_KEY header |

## Output Format

```json
{
  "answer": "The agent's answer",
  "source": "wiki/file.md#section or API endpoint",
  "tool_calls": [...]
}
```

Note: `source` is now optional for system questions.

## Benchmark Strategy

### Initial Run
1. Run `run_eval.py` to get baseline score
2. Document failures in plan

### Iteration Process
1. Analyze failed questions
2. Identify root cause (wrong tool, bad prompt, etc.)
3. Fix and re-run
4. Repeat until all 10 questions pass

### Expected Iterations
- Iteration 1: Baseline (~30-50%)
- Iteration 2: Fix tool descriptions (~60-70%)
- Iteration 3: Improve system prompt (~80-90%)
- Iteration 4: Edge cases (~100%)

## Testing Strategy

### Test 1: Static system question
- Question: "What Python web framework does the backend use?"
- Expected: `read_file` tool call, answer contains "FastAPI"

### Test 2: Data question
- Question: "How many items are in the database?"
- Expected: `query_api` tool call with GET /items/

## Implementation Steps

1. [ ] Создать `plans/task-3.md`
2. [ ] Добавить `query_api` tool schema
3. [ ] Реализовать `query_api` функцию с аутентификацией
4. [ ] Обновить загрузку env variables (LMS_API_KEY, AGENT_API_BASE_URL)
5. [ ] Обновить системный промпт
6. [ ] Обновить `AGENT.md` (минимум 200 слов)
7. [ ] Написать 2 regression теста
8. [ ] Запустить `run_eval.py`, зафиксировать baseline
9. [ ] Итерировать до 100%
10. [ ] Git workflow

## Dependencies
- Существующие: `httpx`, `python-dotenv`
- Новые: не требуются

## Files to Modify
- `agent.py` — добавить query_api и env vars
- `AGENT.md` — документация
- `test_agent.py` — новые тесты
- `.env.agent.secret` — добавить LMS_API_KEY (опционально для локального тестирования)
