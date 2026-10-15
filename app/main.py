import asyncio

from app.agent import Agent


async def main() -> None:
    agent = Agent()

    await agent.memory_store.initialize()

    try:
        conversation_id = "demo-conversation-001"

        # first = await agent.run(
        #     "我叫小王，在北京工作。",
        #     conversation_id=conversation_id,
        # )
        # print("第一轮回答：", first)

        second = await agent.run(
            "我在哪个城市工作？",
            conversation_id=conversation_id,
        )
        print("第二轮回答：", second)

    finally:
        await agent.memory_store.close()


if __name__ == "__main__":
    asyncio.run(main())