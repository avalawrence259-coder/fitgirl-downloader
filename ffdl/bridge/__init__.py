"""
ffdl.bridge - Native Messaging IPC Bridge and Daemon Subsystem
==============================================================
Provides high-throughput Native Messaging IPC framing and authenticated
loopback RPC daemon for seamless browser companion extension integration.
"""

from ffdl.bridge.protocol import (
    MAX_MESSAGE_SIZE,
    MessageType,
    encode_message,
    decode_message,
    read_message,
    write_message,
    validate_payload,
)
from ffdl.bridge.auth import (
    get_or_create_auth_token,
    verify_auth_token,
    get_auth_file_path,
)
from ffdl.bridge.server import BridgeServer, run_bridge_server
from ffdl.bridge.native_host import NativeMessagingHost

__all__ = [
    "MAX_MESSAGE_SIZE",
    "MessageType",
    "encode_message",
    "decode_message",
    "read_message",
    "write_message",
    "validate_payload",
    "get_or_create_auth_token",
    "verify_auth_token",
    "get_auth_file_path",
    "BridgeServer",
    "run_bridge_server",
    "NativeMessagingHost",
]
