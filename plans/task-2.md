# Task 2 Plan: The Documentation Agent

## Overview
Добавить инструменты `read_file` и `list_files` к агенту и реализовать агентовый цикл для навигации по wiki проекта.

## Architecture

### Agentic Loop
```
1. User question → LLM (с определениями инструментов)
2. LLM возвращает tool_calls? → Выполнить инструменты → Добавить результаты как "tool" сообщения → Шаг 1
3. LLM возвращает текстовый ответ? → Извлечь answer + source → Вывести JSON → Конец
4. Максимум 10 вызовов инструментов
```

### Tools

#### read_file
- **Параметры:** `path` (string) — относительный путь от корня
- **Возврат:** содержимое файла или ошибка
- **Безопасность:** проверка на `../` и абсолютные пути

#### list_files
- **Параметры:** `path` (string) — путь к директории
- **Возврат:** список файлов/директорий через newline
- **Безопасность:** проверка на `../` и абсолютные пути

### Function Calling Schema
```json
{
  "name": "read_file",
  "description": "Read contents of a file",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative path from project root"}
    },
    "required": ["path"]
  }
}
```

### System Prompt
- Использовать `list_files` для обнаружения файлов в wiki/
- Использовать `read_file` для чтения содержимого
- Включать `source` с путем к файлу и якорем раздела
- Не выходить за пределы проекта

## Security

| Threat | Mitigation |
|--------|------------|
| Path traversal (`../`) | Проверка пути на `..` |
| Absolute paths | Проверка на начало с `/` или буквы диска |
| Symlinks outside project | Разрешать только внутри проекта |

## Output Format
```json
{
  "answer": "...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Testing Strategy

### Test 1: read_file вызов
- Вопрос: "How do you resolve a merge conflict?"
- Ожидается: `read_file` в tool_calls, `wiki/git-workflow.md` в source

### Test 2: list_files вызов
- Вопрос: "What files are in the wiki?"
- Ожидается: `list_files` в tool_calls

## Implementation Steps

1. [ ] Создать `plans/task-2.md`
2. [ ] Добавить tool schemas в agent.py
3. [ ] Реализовать функции `read_file` и `list_files`
4. [ ] Реализовать агентовый цикл
5. [ ] Обновить системный промпт
6. [ ] Обновить output JSON (добавить `source`)
7. [ ] Написать 2 регрессионных теста
8. [ ] Обновить `AGENT.md`
9. [ ] Git workflow

## Dependencies
- Существующие: `httpx`, `python-dotenv`
- Новые: не требуются
