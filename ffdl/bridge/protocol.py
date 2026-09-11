"""
ffdl.bridge.protocol - Native Messaging Wire Protocol & Framing
===============================================================
Encodes and decodes Chrome/Firefox Native Messaging 32-bit unsigned
integer length-prefixed JSON frames with strict 1MB size bounds checking.
"""

from __future__ import annotations

import enum
import json
import struct
import sys
from typing import Any, BinaryIO, Dict, Optional, Tuple

MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MB boundary


class MessageType(str, enum.Enum):
    PING = "PING"
    PONG = "PONG"
    QUEUE_DOWNLOAD = "QUEUE_DOWNLOAD"
    DOWNLOAD_QUEUED = "DOWNLOAD_QUEUED"
    DOWNLOAD_PROGRESS = "DOWNLOAD_PROGRESS"
    DOWNLOAD_COMPLETE = "DOWNLOAD_COMPLETE"
    DOWNLOAD_ERROR = "DOWNLOAD_ERROR"
    GET_STATUS = "GET_STATUS"
    STATUS_RESPONSE = "STATUS_RESPONSE"
    ERROR = "ERROR"


def encode_message(message: Dict[str, Any]) -> bytes:
    """
    Serializes a Python dict to UTF-8 JSON and prefixes with a 4-byte
    unsigned 32-bit integer length (native byte order).
    Raises ValueError if payload exceeds 1MB.
    """
    json_bytes = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    length = len(json_bytes)
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(
            f"Message size {length} bytes exceeds maximum allowed {MAX_MESSAGE_SIZE} bytes (1MB)"
        )
    header = struct.pack("=I", length)
    return header + json_bytes


def decode_message(raw_bytes: bytes) -> Tuple[Dict[str, Any], int]:
    """
    Decodes a message from bytes prefixed with a 4-byte length.
    Returns (message_dict, total_consumed_bytes).
    Raises ValueError if incomplete or exceeds 1MB.
    """
    if len(raw_bytes) < 4:
        raise ValueError("Incomplete frame: less than 4-byte header received")

    (length,) = struct.unpack("=I", raw_bytes[:4])
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(
            f"Declared message size {length} bytes exceeds maximum allowed {MAX_MESSAGE_SIZE} bytes"
        )

    if len(raw_bytes) < 4 + length:
        raise ValueError(
            f"Incomplete payload: expected {length} bytes, have {len(raw_bytes) - 4} bytes"
        )

    payload_bytes = raw_bytes[4 : 4 + length]
    payload = json.loads(payload_bytes.decode("utf-8"))
    return payload, 4 + length


def read_message(stream: BinaryIO = sys.stdin.buffer) -> Optional[Dict[str, Any]]:
    """
    Reads a single framed message from a binary input stream (e.g. sys.stdin.buffer).
    Returns None if stream is closed (EOF).
    Raises ValueError if message exceeds 1MB or is malformed.
    """
    raw_length = stream.read(4)
    if not raw_length or len(raw_length) < 4:
        return None

    (length,) = struct.unpack("=I", raw_length)
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(
            f"Incoming message size {length} bytes exceeds maximum {MAX_MESSAGE_SIZE} bytes"
        )

    content = stream.read(length)
    if len(content) < length:
        raise ValueError(f"Stream truncated: expected {length} bytes, received {len(content)}")

    return json.loads(content.decode("utf-8"))


def write_message(message: Dict[str, Any], stream: BinaryIO = sys.stdout.buffer):
    """
    Encodes and writes a framed message to a binary output stream, then flushes.
    """
    data = encode_message(message)
    stream.write(data)
    stream.flush()


def validate_payload(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates that the incoming message payload has the required fields.
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    action = payload.get("action") or payload.get("type")
    if not action:
        return False, "Payload missing 'action' or 'type' field"

    if action in (MessageType.QUEUE_DOWNLOAD.value, "download", "queue"):
        url = payload.get("url")
        if not url or not isinstance(url, str):
            return False, "Missing or invalid 'url' in queue request"

    return True, None
