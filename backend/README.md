# AI狼人杀·大师竞技场 后端

FastAPI 后端负责裁判态、板子配置、AI 会话隔离、离线策略兜底和 OpenAI-compatible 模型调用。

## 运行

```bash
cd backend
uv run uvicorn src.api.app:app --reload --host 127.0.0.1 --port 8000
```

## 测试

```bash
cd backend
uv run pytest
```
