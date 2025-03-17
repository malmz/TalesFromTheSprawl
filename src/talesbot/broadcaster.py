import asyncio
from collections.abc import Generator
from typing import Any

from discord import Guild, Message, TextChannel


class Broadcaster:
    store: dict[str, dict[int, TextChannel]] = dict()

    def __init__(self) -> None:
        pass

    def add_channel(self, topic: str, channel: TextChannel):
        topic_store = self.store.setdefault(topic, dict())
        topic_store[channel.id] = channel

    def remove_channel(self, topic: str, channel: TextChannel):
        topic_store = self.store.get(topic)
        if topic_store is not None:
            del topic_store[channel.id]

    def remove_guild(self, guild: Guild):
        for t, ts in self.store.items():
            self.store[t] = {cid: c for cid, c in ts.items() if c.guild.id != guild.id}

    def get_channel_topics(self, channel: TextChannel) -> Generator[str, Any]:
        for topic, topic_store in self.store.items():
            if channel.id in topic_store:
                yield topic

    async def broadcast(self, topic: str, sender_name: str, message: Message):
        topic_store = self.store.get(topic)
        if topic_store is None:
            raise RuntimeError(f"Non-existing topic {topic}")

        files = [await a.to_file() for a in message.attachments]

        async with asyncio.TaskGroup() as tg:
            for c in topic_store.values():
                tg.create_task(
                    c.send(
                        f"<{sender_name}> {message.content}",
                        files=files,
                    )
                )
