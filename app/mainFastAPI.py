# app/main.py

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from app.exceptions import LLMConfigError
from app.llm import GroqClient
from app.logger import get_logger
from app.models import ChatRequest, ChatResponse
from app.service import ChatService
from app.sse import format_sse


load_dotenv()

logger = get_logger(__name__)


app = FastAPI(
    title="Groq AI Chat Backend",
    version="2.0.0",
)


def create_chat_service() -> ChatService:
    """
    创建 ChatService。

    这里负责依赖组装：

        配置
         ↓
        GroqClient
         ↓
        ChatService
    """

    model = os.getenv("GROQ_MODEL")

    if not model:
        raise LLMConfigError(
            "GROQ_MODEL 未配置，请检查 .env"
        )

    llm = GroqClient(
        model=model
    )

    return ChatService(llm)


chat_service = create_chat_service()


@app.get("/health")
async def health() -> dict[str, str]:
    """
    健康检查。
    """

    return {
        "status": "ok",
        "service": "groq-ai-chat",
    }


@app.post(
    "/api/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
) -> ChatResponse:
    """
    普通 Chat API。
    """

    try:

        logger.info(
            "普通 Chat 请求 user_id=%s",
            request.user_id,
        )

        return await chat_service.generate_reply(
            request
        )

    except Exception as error:

        logger.exception(
            "Chat 请求失败"
        )

        raise HTTPException(
            status_code=502,
            detail=f"LLM request failed: {error}",
        ) from error


async def generate_sse(
    request: ChatRequest,
) -> AsyncGenerator[str, None]:
    """
    将 Service 的 token 转换成 SSE。
    """

    try:

        async for token in (
            chat_service.stream_reply(request)
        ):

            yield format_sse(
                {
                    "type": "token",
                    "content": token,
                }
            )

        yield format_sse(
            {
                "type": "done",
            }
        )

    except Exception as error:

        logger.exception(
            "Streaming Chat 请求失败"
        )

        yield format_sse(
            {
                "type": "error",
                "message": str(error),
            }
        )


@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
) -> StreamingResponse:
    """
    SSE 流式 Chat API。
    """

    return StreamingResponse(
        generate_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )