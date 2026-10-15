import json
from typing import Any


def format_sse(data: dict[str, Any]) -> str:
    # SSE 一个完整事件以两个换行符结束。
    payload = json.dumps(data, ensure_ascii=False)
    return f"data: {payload}\n\n"
