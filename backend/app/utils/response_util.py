import uuid
from datetime import datetime

# 引入新的模型名称
from schemas.response import (
    ContentKind,
    FinishMessageBody,
    PacketMeta,
    StreamPacket,
    StreamStatus,
    StructuredMessageBody,
    TextMessageBody,
)


class ResponseFactory:
    """
    SSE 响应构建工厂
    """

    @staticmethod
    def build_text(text: str, kind: ContentKind) -> StreamPacket:
        """
        构建文本/推理片段响应
        """
        body = TextMessageBody(
            text=text,
            kind=kind
        )

        return StreamPacket(
            id=str(uuid.uuid4()),
            content=body,
            status=StreamStatus.IN_PROGRESS,
            metadata=PacketMeta(createTime=str(datetime.now()))
        )

    @staticmethod
    def build_finish(message_id: str | None = None) -> StreamPacket:
        """
        构建结束信号响应
        """
        if message_id is None:
            message_id = str(uuid.uuid4())

        return StreamPacket(
            id=message_id,
            content=FinishMessageBody(),
            status=StreamStatus.FINISHED,
            metadata=PacketMeta(createTime=str(datetime.now()))
        )

    @staticmethod
    def build_structured(card_type: str, data: dict) -> StreamPacket:
        """构建结构化数据响应"""
        body = StructuredMessageBody(
            card_type=card_type,
            data=data
        )
        return StreamPacket(
            id=str(uuid.uuid4()),
            content=body,
            status=StreamStatus.IN_PROGRESS,
            metadata=PacketMeta(createTime=str(datetime.now()))
        )