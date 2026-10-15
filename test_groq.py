import asyncio
import os

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()


async def main() -> None:
    # 用这个脚本快速判断 API Key、模型和网络是否正常。
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY 未配置")

    if not model:
        raise RuntimeError("GROQ_MODEL 未配置")

    client = AsyncGroq(api_key=api_key)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "用一句话解释什么是 RAG。",
            }
        ],
    )

    print(response.choices[0].message.content or "")


if __name__ == "__main__":
    asyncio.run(main())
