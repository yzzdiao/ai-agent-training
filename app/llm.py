# app/llm.py

import os
from collections.abc import AsyncGenerator
from typing import Protocol

from dotenv import load_dotenv
from groq import AsyncGroq

from app.exceptions import LLMConfigError


load_dotenv()


class LLMClient(Protocol):
    """
    LLM 统一接口。

    ChatService 不关心底层是：

    Groq
    OpenAI
    Gemini
    DeepSeek
    MockLLM

    它只知道：
    给我 messages，我返回 AI 结果。
    """

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        ...

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        ...


class GroqClient:
    """
    Groq 的具体实现。

    负责：
    - 调用 Groq API
    - 普通生成
    - 流式生成

    不负责：
    - 用户历史记录
    - System Prompt
    - FastAPI
    - SSE
    """

    def __init__(self, model: str):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise LLMConfigError(
                "GROQ_API_KEY 未配置，请检查 .env"
            )

        if not model:
            raise LLMConfigError(
                "GROQ_MODEL 未配置，请检查 .env"
            )

        self.client = AsyncGroq(
            api_key=api_key
        )

        self.model = model

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """
        普通调用。

        messages 现在不再是一个字符串，
        而是完整的 Context。
        """

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )

        return (
            response.choices[0].message.content
            or ""
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用。

        模型生成一点，就 yield 一点。
        """

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )

        async for chunk in stream:

            if not chunk.choices:
                continue

            content = (
                chunk.choices[0]
                .delta.content
            )

            if content:
                yield content