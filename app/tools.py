from typing import Any


def get_weather(city: str) -> dict[str, Any]:
    """查询指定城市的模拟天气。"""
    return {"city": city, "weather": "晴天", "temperature": 25}


def get_air_quality(city: str) -> dict[str, Any]:
    """查询指定城市的模拟空气质量。"""
    return {"city": city, "aqi": 45, "level": "优"}


# 模型只能请求应用明确注册的工具。
TOOLS = {
    "get_weather": get_weather,
    "get_air_quality": get_air_quality,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名称"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_air_quality",
            "description": "查询指定城市的空气质量",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名称"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    },
]
