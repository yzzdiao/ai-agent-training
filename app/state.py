from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    """记录一次 Agent 任务的执行状态。"""

    messages: list[dict[str, Any]] = field(default_factory=list)
    step_count: int = 0
    tool_call_count: int = 0
    status: str = "running"
