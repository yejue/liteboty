import json
import time

from enum import Enum

import numpy as np

from typing import Any, Optional, Dict

from .protos.message_pb2 import Message as ProtoMessage
from .protos.message_pb2 import Metadata as ProtoMetadata


class MessageType(Enum):
    JSON = ProtoMessage.JSON
    IMAGE = ProtoMessage.IMAGE
    BINARY = ProtoMessage.BINARY
    NUMPY = ProtoMessage.NUMPY


class Message:
    def __init__(
            self,
            data: Any,
            msg_type: MessageType,
            metadata: Optional[Dict] = None
    ):
        self.data = data
        self.msg_type = msg_type
        self.metadata = metadata or {}

    @staticmethod
    def encode(msg: 'Message') -> bytes:
        proto_msg = ProtoMessage()
        proto_msg.type = msg.msg_type.value

        # 设置元数据
        metadata = ProtoMetadata()
        metadata.timestamp = int(time.time() * 1000)  # 毫秒时间戳
        metadata.version = msg.metadata.get('version', '1.0')
        for key, value in msg.metadata.items():
            metadata.attributes[key] = str(value)
        proto_msg.metadata.CopyFrom(metadata)

        # 处理数据
        if msg.msg_type == MessageType.JSON:
            proto_msg.data = json.dumps(msg.data).encode('utf-8')
        elif msg.msg_type == MessageType.IMAGE:
            proto_msg.data = msg.data
        elif msg.msg_type == MessageType.NUMPY:
            buffer = msg.data.tobytes()
            shape = msg.data.shape
            dtype = str(msg.data.dtype)
            array_meta = json.dumps({
                'shape': shape,
                'dtype': dtype
            }).encode('utf-8')
            proto_msg.data = array_meta + buffer
        else:
            proto_msg.data = msg.data if isinstance(msg.data, bytes) else str(msg.data).encode()

        return proto_msg.SerializeToString()

    @staticmethod
    def decode(data: bytes) -> 'Message':
        proto_msg = ProtoMessage()
        proto_msg.ParseFromString(data)

        metadata = {
            'timestamp': proto_msg.metadata.timestamp,
            'version': proto_msg.metadata.version,
            **proto_msg.metadata.attributes
        }

        msg_type = MessageType(proto_msg.type)

        if msg_type == MessageType.JSON:
            decoded_data = json.loads(proto_msg.data.decode('utf-8'))
        elif msg_type == MessageType.IMAGE:
            decoded_data = proto_msg.data
        elif msg_type == MessageType.NUMPY:
            meta_end = proto_msg.data.find(b'}') + 1
            array_meta = json.loads(proto_msg.data[:meta_end].decode('utf-8'))
            buffer = proto_msg.data[meta_end:]
            decoded_data = np.frombuffer(buffer, dtype=array_meta['dtype']).reshape(array_meta['shape'])
        else:
            decoded_data = proto_msg.data

        return Message(decoded_data, msg_type, metadata)
