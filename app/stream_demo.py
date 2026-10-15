import asyncio
from collections.abc import AsyncGenerator


async def generate_tokens() -> AsyncGenerator[str, None]:
    """
    模拟 LLM 流式生成 Token。
    """

    tokens = [
        "你好",
        "，",
        "我是",
        "一个",
        "AI",
        "助手",
        "。",
    ]

    for token in tokens:
        await asyncio.sleep(0.5)

        yield token


async def main() -> None:
    async for token in generate_tokens():
        print(token, end="", flush=True)

    print()


if __name__ == "__main__":
    asyncio.run(main())