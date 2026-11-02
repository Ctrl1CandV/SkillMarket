"""Bounded stdio transport for the official Codex app-server (standard library only)."""
from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import queue
import subprocess
import threading
import time

from .common import Error


class AppServer:
    def __init__(self, command: list[str], cwd: Path):
        self.process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", bufsize=1)
        assert self.process.stdin is not None and self.process.stdout is not None and self.process.stderr is not None
        self.stdin, self.stdout, self.stderr = self.process.stdin, self.process.stdout, self.process.stderr
        self.messages = queue.Queue(maxsize=64)
        self.events = deque()
        self.sequence = 0
        self.diagnostic_bytes = 0
        self.cleanup = "running"
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.errors = threading.Thread(target=self._drain_errors, daemon=True)
        self.reader.start()
        self.errors.start()

    def _read(self):
        while True:
            line = self.stdout.readline(64 * 1024 * 1024 + 1)
            if not line:
                self.messages.put(None)
                return
            if len(line) > 64 * 1024 * 1024:
                self.messages.put({"transport_error": "oversized app-server message"})
                return
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("Expected an event object")
                self.messages.put(value)
            except ValueError:
                self.messages.put({"transport_error": "non-object/invalid JSON app-server output"})
                return

    def _drain_errors(self):
        # Drain, but do not store or print diagnostics that might contain private configuration.
        while block := self.stderr.read(4096):
            self.diagnostic_bytes += len(block)

    def send(self, value: dict):
        try:
            self.stdin.write(json.dumps(value, ensure_ascii=True) + "\n")
            self.stdin.flush()
        except (OSError, ValueError):
            raise Error("App-server write failed; inspect the saved thread, never resubmit") from None

    def next(self, timeout: float):
        try:
            message = self.messages.get(timeout=max(0.001, timeout))
        except queue.Empty:
            raise Error("App-server wait timed out; inspect the saved thread, never resubmit") from None
        if message is None or "transport_error" in message:
            raise Error("App-server disconnected or returned an invalid message; inspect the saved thread")
        return message

    def rpc(self, method: str, params: dict, timeout: float = 45):
        self.sequence += 1
        ident = self.sequence
        self.send({"id": ident, "method": method, "params": params})
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            message = self.next(end - time.monotonic())
            if message.get("id") == ident and "method" not in message:
                if "error" in message:
                    # Do not expose server-provided bodies/URLs/credentials in errors.
                    error = message["error"]
                    code = error.get("code") if isinstance(error, dict) else None
                    code = code if isinstance(code, int) else "unknown"
                    raise Error(f"{method} RPC failed (code {code})")
                result = message.get("result", {})
                if not isinstance(result, dict):
                    raise Error(f"{method} returned an invalid response object")
                return result
            if len(self.events) >= 128:
                raise Error("Too many unconsumed app-server events")
            self.events.append(message)
        raise Error(f"{method} timed out; do not resubmit")

    def close(self):
        try:
            self.stdin.close()
        except OSError:
            pass
        try:
            self.process.wait(timeout=10)
            self.cleanup = "exited_after_stdin_close"
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
            self.cleanup = "terminated_own_process"
        self.reader.join(timeout=2)
        self.errors.join(timeout=2)
        for stream in (self.stdout, self.stderr):
            stream.close()
