import asyncio
import json
import logging
import os
import random
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from groq import (
    AsyncGroq,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from app import state
from app.state import AgentState
from app.tools import TOOLS, TOOL_SCHEMAS
from app.memory import PostgresMemoryStore
from app.context import ContextManager

load_dotenv()
logger = logging.getLogger(__name__)

RETRYABLE_ERRORS = (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)


class Agent:
    """支持多轮工具调用、超时和有限重试的 Groq Agent。"""

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL")
        

        if not api_key:
            raise RuntimeError("缺少 GROQ_API_KEY，请检查 .env 文件")
        if not model:
            raise RuntimeError("缺少 GROQ_MODEL，请检查 .env 文件")

        # 关闭 SDK 自动重试，避免与应用层重试叠加。
        self.client = AsyncGroq(api_key=api_key, timeout=20.0, max_retries=0)
        self.model = model
        self.max_retries = 3
        self.max_steps = 5
        self.max_tool_calls = 10
        self.request_timeout = 20.0
        self.memory_store = PostgresMemoryStore()
        self.context_manager = ContextManager(max_user_turns=8)

    async def request_model(self, messages: list[dict[str, Any]]) -> Any:
        """对可恢复的模型请求错误进行有限次重试。"""
        for attempt in range(self.max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=TOOL_SCHEMAS,
                        tool_choice="auto",
                    ),
                    timeout=self.request_timeout,
                )
            except asyncio.TimeoutError:
                error_name = "asyncio.TimeoutError"
            except RETRYABLE_ERRORS as error:
                error_name = type(error).__name__
            except APIStatusError as error:
                # 仅对临时服务端状态码重试；认证和参数错误直接抛出。
                if error.status_code not in {500, 502, 503, 504}:
                    raise
                error_name = f"APIStatusError({error.status_code})"

            if attempt >= self.max_retries:
                logger.error("模型请求重试耗尽，尝试次数=%s", attempt + 1)
                raise RuntimeError(
                    f"模型请求失败，已尝试 {attempt + 1} 次"
                )

            delay = min(2 ** attempt, 8) + random.uniform(0, 0.5)
            logger.warning(
                "模型请求暂时失败：%s；第 %s 次尝试，%.2f 秒后重试",
                error_name, attempt + 1, delay,
            )
            await asyncio.sleep(delay)

        raise RuntimeError("模型请求意外退出重试循环")

    @staticmethod
    def _validate_arguments(tool_name: str, arguments: Any) -> dict[str, Any]:
        """校验工具参数，并拒绝未知字段。"""
        if not isinstance(arguments, dict):
            raise ValueError("工具参数必须是 JSON 对象")
        if tool_name not in TOOLS:
            raise ValueError(f"未知工具：{tool_name}")
        if set(arguments) != {"city"}:
            raise ValueError("工具参数必须且只能包含 city")

        city = arguments.get("city")
        if not isinstance(city, str) or not city.strip():
            raise ValueError("city 必须是非空字符串")
        return {"city": city.strip()}

    async def _execute_tool(
        self, tool_name: str, raw_arguments: str
    ) -> dict[str, Any]:
        """执行白名单工具；单个工具失败不会直接打断 Agent Loop。"""
        try:
            arguments = json.loads(raw_arguments)
            validated = self._validate_arguments(tool_name, arguments)
            result = TOOLS[tool_name](**validated)
            return {"ok": True, "data": result}
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            logger.warning("工具参数错误，tool_name=%s：%s", tool_name, error)
            return {"ok": False, "error": str(error)}
        except Exception:
            # 详细异常写入服务端日志，不将堆栈暴露给模型。
            logger.exception("工具执行失败，tool_name=%s", tool_name)
            return {
                "ok": False,
                "error": f"工具 {tool_name} 执行失败，请考虑其他方案。",
            }

    async def run(self, user_message: str, conversation_id: str) -> str:
        """运行 Agent Loop，直到模型回答或达到执行上限。"""
        if not user_message.strip():
            raise ValueError("user_message 不能为空")

        if not conversation_id.strip():
            raise ValueError("conversation_id 不能为空")
        # 读取该会话之前的对话历史。
        messages = await self.memory_store.load(conversation_id)
        # 只有新会话才初始化系统提示词。
        if not messages:
            messages.append({
                "role": "system",
                "content": (
                    "你是一个 AI 助手。"
                    "需要天气信息时调用 get_weather；"
                    "需要空气质量时调用 get_air_quality。"
                    "这些工具返回模拟数据，不代表实时情况。"
                    "只能根据工具结果描述查询到的信息，不要编造数据。"
                ),
            })

        # 把本轮用户消息追加到已有历史中。
        messages.append({
            "role": "user",
            "content": user_message,
        })

        state = AgentState(
            messages=messages,
        )

        while state.step_count < self.max_steps:
            state.step_count += 1
            logger.info("Agent 决策轮次：%s", state.step_count)

            context_messages = self.context_manager.build(state.messages)

            logger.info(
                "上下文裁剪完成：完整消息数=%s，本次发送=%s",
                len(state.messages),
                len(context_messages),
            )

            response = await self.request_model(context_messages)
            assistant_message = response.choices[0].message
            state.messages.append(assistant_message.model_dump(exclude_none=True))
            if assistant_message.tool_calls:
                logger.info(
                    "本轮模型决定调用 %s 个工具：%s",
                    len(assistant_message.tool_calls),
                    [
                        tool_call.function.name
                        for tool_call in assistant_message.tool_calls
                    ],
                )
            else:
                logger.info("本轮模型决定直接生成最终回答")

            if not assistant_message.tool_calls:
                state.status = "completed"
                await self.memory_store.save(
                    conversation_id,
                    state.messages,
                )
                return assistant_message.content or ""

            for tool_call in assistant_message.tool_calls:
                state.tool_call_count += 1
                if state.tool_call_count > self.max_tool_calls:
                    state.status = "limit_reached"
                    return "工具调用次数已达上限，请缩小任务范围后重试。"

                tool_result = await self._execute_tool(
                    tool_call.function.name,
                    tool_call.function.arguments,
                )
                state.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

        state.status = "limit_reached"
        await self.memory_store.save(conversation_id, state.messages)
        logger.warning(
            "Agent 达到最大决策轮数：steps=%s tools=%s",
            state.step_count, state.tool_call_count,
        )
        return "Agent 已达到最大执行步数，请缩小任务范围后重试。"
