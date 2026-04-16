"""用于解耦渠道（channel）和代理（agent）通信的异步消息队列。"""

import asyncio

from nanobot.bus.events import InboundMessage, OutboundMessage


class MessageBus:
    """
    异步消息总线，用于将聊天渠道与代理核心解耦。

    渠道将消息推送到入站队列（inbound queue），代理处理这些消息，
    并将响应推送到出站队列（outbound queue）。
    """

    def __init__(self):
        # 入站消息队列：用于存放从各个渠道接收到的消息，等待代理处理
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        # 出站消息队列：用于存放代理处理完毕准备发送给渠道的消息
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """发布一条从渠道发往代理的入站消息。"""
        await self.inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """消费下一条入站消息（如果队列为空则阻塞等待）。"""
        return await self.inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """发布一条从代理发往渠道的出站响应消息。"""
        await self.outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """消费下一条出站消息（如果队列为空则阻塞等待）。"""
        return await self.outbound.get()

    @property
    def inbound_size(self) -> int:
        """当前待处理的入站消息数量。"""
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        """当前待处理的出站消息数量。"""
        return self.outbound.qsize()
