import asyncio
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse


app = FastAPI()


async def generate_tokens() -> AsyncGenerator[str, None]:
    """
    模拟 LLM 流式输出。
    """

    tokens = [
        "你好",
        "，",
        "我是",
        "AI",
        "助手",
        "。",
    ]

    for token in tokens:
        await asyncio.sleep(0.5)

        yield token


@app.get("/api/chat/stream")
async def chat_stream() -> StreamingResponse:
    """
    流式聊天接口。
    """

    return StreamingResponse(
        generate_tokens(),
        media_type="text/plain",
    )