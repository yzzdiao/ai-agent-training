# app/service.py

from collections.abc import AsyncGenerator

from app.llm import LLMClient
from app.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from app.prompts import SYSTEM_PROMPT


class ChatService:
    """
    Chat 业务层。

    这里负责构建真正发送给 LLM 的 Context。

    Context：

        System Prompt
             +
        History
             +
        Current User Message
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def build_messages(
        self,
        request: ChatRequest,
    ) -> list[dict[str, str]]:
        """
        构建发送给 LLM 的完整 messages。

        注意：

        System Prompt 永远由后端控制，
        不允许客户端直接传入。
        """

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        # 加入历史消息
        for item in request.history:

            messages.append(
                {
                    "role": item.role,
                    "content": item.content,
                }
            )

        # 最后加入当前用户消息
        messages.append(
            {
                "role": "user",
                "content": request.message,
            }
        )

        return messages

    async def generate_reply(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        普通生成。
        """

        messages = self.build_messages(request)

        result = await self.llm.generate(
            messages=messages,
            temperature=request.temperature,
        )

        return ChatResponse(
            message=result,
            model=request.model or "default",
        )

    async def stream_reply(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[str, None]:
        """
        流式生成。
        """

        messages = self.build_messages(request)

        async for token in self.llm.stream(
            messages=messages,
            temperature=request.temperature,
        ):
            yield token