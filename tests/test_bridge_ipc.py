"""
Unit tests for Native Messaging IPC protocol framing, length validation, and serialization.
"""

import io
import pytest
from ffdl.bridge.protocol import (
    MAX_MESSAGE_SIZE,
    MessageType,
    encode_message,
    decode_message,
    read_message,
    write_message,
    validate_payload,
)


def test_encode_decode_roundtrip():
    msg = {
        "action": "QUEUE_DOWNLOAD",
        "url": "https://fitgirl-repacks.site/prince-of-persia-the-lost-crown/",
        "hoster": "fuckingfast",
        "main_only": True,
    }
    encoded = encode_message(msg)
    # Header is 4 bytes
    assert len(encoded) > 4
    decoded, consumed = decode_message(encoded)
    assert consumed == len(encoded)
    assert decoded["action"] == "QUEUE_DOWNLOAD"
    assert decoded["url"] == msg["url"]
    assert decoded["hoster"] == "fuckingfast"
    assert decoded["main_only"] is True


def test_max_message_size_enforcement():
    # Exactly 1 MB should be within limit (or slightly under)
    huge_data = {"action": "PING", "payload": "A" * (MAX_MESSAGE_SIZE + 100)}
    with pytest.raises(ValueError, match="exceeds maximum"):
        encode_message(huge_data)


def test_decode_bounds_and_incomplete_packets():
    with pytest.raises(ValueError, match="less than 4-byte header"):
        decode_message(b"12")

    # Incomplete body
    import struct
    fake_header = struct.pack("=I", 100)
    with pytest.raises(ValueError, match="Incomplete payload"):
        decode_message(fake_header + b"short")


def test_stream_read_write():
    stream = io.BytesIO()
    msg = {"action": "PING"}
    write_message(msg, stream)
    stream.seek(0)
    read_msg = read_message(stream)
    assert read_msg == msg


def test_payload_validation():
    valid, err = validate_payload({"action": "PING"})
    assert valid is True
    assert err is None

    valid, err = validate_payload({"action": "QUEUE_DOWNLOAD", "url": "https://example.com"})
    assert valid is True

    valid, err = validate_payload({"action": "QUEUE_DOWNLOAD"})
    assert valid is False
    assert "Missing or invalid 'url'" in err

    valid, err = validate_payload("not a dict")
    assert valid is False
