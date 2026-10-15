
from typing import Any


Message = dict[str, Any]


class ContextManager:
    """从完整对话历史中挑选本次请求需要的上下文。"""

    def __init__(self, max_user_turns: int = 8) -> None:
        if max_user_turns < 1:
            raise ValueError("max_user_turns 必须大于 0")
        self.max_user_turns = max_user_turns

    def build(self, messages: list[Message]) -> list[Message]:
        # 系统提示词始终保留。
        system_messages = [
            message
            for message in messages
            if message.get("role") == "system"
        ]

        # 找到每一轮用户消息的位置。
        user_indexes = [
            index
            for index, message in enumerate(messages)
            if message.get("role") == "user"
        ]

        if len(user_indexes) <= self.max_user_turns:
            return list(messages)

        # 从最近 N 轮中的第一条用户消息开始截取。
        start_index = user_indexes[-self.max_user_turns]
        recent_messages = messages[start_index:]

        # 系统提示词与最近对话组成最终上下文。
        return system_messages + recent_messages
