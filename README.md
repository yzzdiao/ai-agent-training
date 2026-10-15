# Groq AI Chat Backend

第 10 课可直接运行项目：FastAPI + Pydantic + AsyncGroq + SSE。

## 快速开始

1. Python 3.10+
2. `pip install -r requirements.txt`
3. 复制 `.env.example` 为 `.env`
4. 填入你的 `GROQ_API_KEY`
5. 按需修改 `GROQ_MODEL`
6. `uvicorn app.main:app --reload`

Swagger:
`http://127.0.0.1:8000/docs`

健康检查:
`http://127.0.0.1:8000/health`

## Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API

### POST /api/chat

```json
{
  "message": "请用简单的语言解释什么是 RAG",
  "user_id": "user-001",
  "temperature": 0.7
}
```

### POST /api/chat/stream

SSE 流式输出。可以运行：

```bash
python test_stream.py
```

## 项目结构

```text
groq-ai-chat-project/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── llm.py
│   ├── service.py
│   ├── sse.py
│   ├── exceptions.py
│   └── logger.py
├── .env.example
├── .gitignore
├── requirements.txt
├── test_groq.py
├── test_stream.py
└── README.md
```

## 架构

```text
Client
  ↓
FastAPI
  ↓
Pydantic
  ↓
ChatService
  ↓
LLMClient
  ↓
GroqClient
  ↓
Groq API
  ↓
LLM
```

流式：

```text
Groq stream
  ↓
async for
  ↓
yield
  ↓
SSE
  ↓
Browser
```

## 为什么要 LLMClient

ChatService 依赖抽象，而不是直接依赖 Groq。以后可以增加：

```text
GroqClient
OpenAIClient
GeminiClient
MockLLM
```

而不需要重写业务层。

## 安全

不要把真实 API Key 提交到 Git。`.env` 已加入 `.gitignore`。

如果 API Key 已经泄露，应在 Groq 控制台撤销/轮换。

## 本课重点

- async / await
- AsyncGroq
- Chat Completions
- streaming
- async generator / yield
- SSE
- FastAPI
- Pydantic
- Protocol / Provider Abstraction
