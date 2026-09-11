"""
ffdl.bridge.native_host - Native Messaging Host Driver
======================================================
Implements Chrome/Firefox Native Messaging host stdin/stdout IPC loop.
Host name: com.ffdl.native_host
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from typing import Any, Dict

from ffdl.bridge.protocol import (
    MessageType,
    read_message,
    write_message,
    validate_payload,
)


class NativeMessagingHost:
    """Chrome/Firefox Native Messaging Host message dispatcher."""

    def __init__(self):
        self.running = True

    def handle_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        valid, err = validate_payload(msg)
        if not valid:
            return {"type": MessageType.ERROR.value, "error": err}

        action = (msg.get("action") or msg.get("type", "")).upper()

        if action in ("PING", MessageType.PING.value):
            return {"type": MessageType.PONG.value, "status": "ok"}

        if action in ("GET_STATUS", MessageType.GET_STATUS.value):
            return {
                "type": MessageType.STATUS_RESPONSE.value,
                "status": "ready",
                "version": "1.0.0",
                "app": "ffdl-native-host",
            }

        if action in ("QUEUE_DOWNLOAD", "DOWNLOAD", "QUEUE", MessageType.QUEUE_DOWNLOAD.value):
            url = msg.get("url", "")
            hoster = msg.get("hoster", "auto")
            main_only = msg.get("main_only", True)
            job_id = f"job-{uuid.uuid4().hex[:8]}"

            queue_dir = os.path.expanduser("~/.ffdl/queue")
            os.makedirs(queue_dir, exist_ok=True)
            job_file = os.path.join(queue_dir, f"{job_id}.json")
            try:
                with open(job_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "id": job_id,
                            "url": url,
                            "hoster": hoster,
                            "main_only": main_only,
                        },
                        f,
                        indent=2,
                    )
            except Exception:
                pass

            return {
                "type": MessageType.DOWNLOAD_QUEUED.value,
                "status": "queued",
                "job_id": job_id,
                "url": url,
                "hoster": hoster,
                "main_only": main_only,
            }

        return {
            "type": MessageType.ERROR.value,
            "error": f"Unknown action: {action}",
        }

    def run(self):
        """Unbuffered binary I/O loop."""
        if sys.platform == "win32":
            import msvcrt
            try:
                msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            except Exception:
                pass

        while self.running:
            try:
                msg = read_message(sys.stdin.buffer)
                if msg is None:
                    break
                response = self.handle_message(msg)
                write_message(response, sys.stdout.buffer)
            except Exception as e:
                try:
                    write_message(
                        {"type": MessageType.ERROR.value, "error": str(e)},
                        sys.stdout.buffer,
                    )
                except Exception:
                    pass
                break


def main():
    host = NativeMessagingHost()
    host.run()


if __name__ == "__main__":
    main()
