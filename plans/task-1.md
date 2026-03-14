# Task 1 Plan: Call an LLM from Code

## Overview
Создать CLI-программу `agent.py`, которая принимает вопрос как аргумент командной строки, отправляет его в LLM через API и возвращает структурированный JSON-ответ.

## Architecture

### Data Flow
```
User (CLI arg) → agent.py → HTTP POST /v1/chat/completions → LLM → JSON response → stdout
```

### Components

1. **Environment Configuration**
   - Загрузка переменных окружения из `.env.agent.secret`
   - Required vars: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

2. **LLM Client**
   - HTTP-клиент для вызова LLM API (используем `httpx`)
   - Формирование запроса в OpenAI-compatible формате

3. **CLI Interface**
   - Приём вопроса как аргумента командной строки
   - Валидация входных данных

4. **Response Handler**
   - Парсинг ответа от LLM
   - Формирование JSON: `{"answer": "...", "tool_calls": []}`

## Error Handling

| Error | Handling |
|-------|----------|
| Missing env vars | Exit code 1, message to stderr |
| HTTP error | Exit code 1, message to stderr |
| Invalid LLM response | Exit code 1, message to stderr |
| No question provided | Exit code 1, usage message to stderr |

## Output Rules
- **stdout**: только валидный JSON
- **stderr**: все debug/log сообщения
- **Exit code**: 0 при успехе, 1 при ошибке
- **Timeout**: 60 секунд на ответ

## Testing Strategy

### Regression Test
- Запустить `agent.py` с тестовым вопросом
- Проверить:
  - Валидный JSON в stdout
  - Наличие поля `answer` (не пустое)
  - Наличие поля `tool_calls` (пустой массив)
  - Exit code 0

## Implementation Steps

1. [ ] Создать `.env.agent.secret` из `.env.agent.example`
2. [ ] Написать `agent.py`:
   - Загрузка env переменных
   - CLI аргументы (argparse или sys.argv)
   - HTTP-запрос к LLM API
   - JSON output
3. [ ] Написать `AGENT.md` с документацией
4. [ ] Написать регрессионный тест
5. [ ] Git workflow: issue → branch → PR → merge

## Dependencies
- `httpx` — уже есть в `pyproject.toml`
- `pydantic-settings` — для загрузки env (опционально)
- `python-dotenv` — если понадобится
