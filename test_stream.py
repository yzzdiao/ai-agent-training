import asyncio
import os

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()


async def main() -> None:
    # 演示最小的异步 Streaming。
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY 未配置")

    if not model:
        raise RuntimeError("GROQ_MODEL 未配置")

    client = AsyncGroq(api_key=api_key)

    stream = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "请用简单语言解释什么是 AI Agent。",
            }
        ],
        stream=True,
    )

    async for chunk in stream:
        if not chunk.choices:
            continue

        content = chunk.choices[0].delta.content

        if content:
            print(content, end="", flush=True)

    print()


if __name__ == "__main__":
    asyncio.run(main())
