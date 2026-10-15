
import json
import os
from pathlib import Path
from typing import Any

import asyncpg
from dotenv import load_dotenv

load_dotenv()


class PostgresMemoryStore:
    """使用 PostgreSQL 持久化 Agent 的完整消息历史。"""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("缺少 DATABASE_URL")

        self.pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """创建连接池并初始化数据库表。"""
        self.pool = await asyncpg.create_pool(
            dsn=self.database_url,
            min_size=1,
            max_size=10,
            command_timeout=10,
        )

        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")

        async with self.pool.acquire() as connection:
            await connection.execute(schema)

    def _get_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("数据库连接池尚未初始化")
        return self.pool

    async def load(
        self,
        conversation_id: str,
    ) -> list[dict[str, Any]]:
        """按顺序读取某个会话的完整消息历史。"""
        pool = self._get_pool()

        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT payload::text AS payload
                FROM messages
                WHERE conversation_id = $1
                ORDER BY sequence_no
                """,
                conversation_id,
            )

        return [json.loads(row["payload"]) for row in rows]

    async def save(
        self,
        conversation_id: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """
        保存完整消息快照。

        教学实现：先删除旧消息，再在同一事务中写入新快照。
        """
        pool = self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """
                    INSERT INTO conversations (id)
                    VALUES ($1)
                    ON CONFLICT (id)
                    DO UPDATE SET updated_at = NOW()
                    """,
                    conversation_id,
                )

                await connection.execute(
                    "DELETE FROM messages WHERE conversation_id = $1",
                    conversation_id,
                )

                for sequence_no, message in enumerate(messages, start=1):
                    role = message.get("role", "unknown")

                    await connection.execute(
                        """
                        INSERT INTO messages (
                            conversation_id,
                            sequence_no,
                            role,
                            payload
                        )
                        VALUES ($1, $2, $3, $4::jsonb)
                        """,
                        conversation_id,
                        sequence_no,
                        role,
                        json.dumps(message, ensure_ascii=False),
                    )

    async def clear(self, conversation_id: str) -> None:
        """删除一个会话及其全部消息。"""
        pool = self._get_pool()

        async with pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM conversations WHERE id = $1",
                conversation_id,
            )

    async def close(self) -> None:
        """释放数据库连接池。"""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None