# app/models.py

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """
    一条历史聊天消息。

    role：
        user      用户
        assistant AI
        system    系统

    content：
        消息具体内容
    """

    role: str = Field(
        description="消息角色，例如 user / assistant / system"
    )

    content: str = Field(
        min_length=1,
        description="消息内容"
    )


class ChatRequest(BaseModel):
    """
    Chat API 请求。

    注意：

    当前用户真正发送的问题仍然使用 message。

    history 用来携带之前的聊天记录。

    System Prompt 不允许由前端传入，
    而是由后端统一控制。
    """

    message: str = Field(
        min_length=1,
        description="当前用户消息"
    )

    user_id: str = Field(
        min_length=1,
        description="用户 ID"
    )

    history: list[ChatMessage] = Field(
        default_factory=list,
        description="历史聊天记录"
    )

    temperature: float = Field(
        default=0.7,
        ge=0,
        le=2,
        description="模型 temperature"
    )

    model: str | None = Field(
        default=None,
        description="模型名称，默认使用后端配置的模型"
    )


class ChatResponse(BaseModel):
    """
    普通 Chat API 返回结果。
    """

    message: str

    model: str