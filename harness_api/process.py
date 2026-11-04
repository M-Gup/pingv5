"""The game's side of one harness process.

Each player's harness runs in its own process (harness_api/runner.py), so that a method
still running at its time limit can be stopped, and so that harness code cannot read the
game's memory. The time limits are measured here, not in the harness process. The
orchestrator (engine/) and the self-check (harness_api/check.py) both use this.

This is a plain local process (local games, tests, the self-check). In the real game the same
runner runs inside each harness's locked-down container and is reached over a WebSocket:
engine/server.py (RemoteHarness, the same interface as this class) and harness_api/client.py.
"""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RUNNER = Path(__file__).resolve().parent / "runner.py"
_EOF = object()


@dataclass(frozen=True)
class CallResult:
    status: str               # "ok" | "error" | "timeout" | "unavailable"
    value: Any = None
    error: str | None = None
    seconds: float = 0.0


class HarnessProcess:
    def __init__(self, submission: Path, log_path: Path, stop_grace_seconds: float):
        self.submission = Path(submission)
        self.log_path = Path(log_path)
        self._grace = stop_grace_seconds
        self._next_id = 0
        self._sent: dict[int, float] = {}
        self._replies: queue.Queue = queue.Queue()
        self._proc: subprocess.Popen | None = None
        self.killed = False

    @property
    def available(self) -> bool:
        return self._proc is not None and self._proc.poll() is None and not self.killed

    def start(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = open(self.log_path, "ab")
        self._proc = subprocess.Popen(
            [sys.executable, "-I", str(RUNNER), str(self.submission)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._log,
        )
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for raw in self._proc.stdout:
            try:
                self._replies.put(json.loads(raw.decode("utf-8")))
            except (ValueError, UnicodeDecodeError):
                pass  # not a protocol line
        self._replies.put(_EOF)

    def _write(self, msg: dict) -> bool:
        if self._proc is None or self._proc.stdin is None:
            return False
        try:
            self._proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
            self._proc.stdin.flush()
            return True
        except (OSError, ValueError):
            return False

    def send(self, method: str, arg: Any = None) -> int | None:
        """Start a call; returns its id, or None if the harness is unavailable."""
        if not self.available:
            return None
        self._next_id += 1
        cid = self._next_id
        if not self._write({"id": cid, "method": method, "arg": arg}):
            return None
        self._sent[cid] = time.monotonic()
        return cid

    def wait(self, cid: int | None, deadline: float) -> CallResult:
        """The reply to call `cid`, or a timeout once `deadline` (time.monotonic()) passes."""
        if cid is None:
            return CallResult("unavailable", error="harness process is not running")
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return CallResult("timeout", error="time limit reached", seconds=self._elapsed(cid))
            try:
                msg = self._replies.get(timeout=remaining)
            except queue.Empty:
                continue
            if msg is _EOF:
                self.killed = True
                return CallResult("unavailable", error="harness process exited", seconds=self._elapsed(cid))
            if msg.get("id") != cid:
                continue  # a late reply to an earlier, stopped call
            if msg.get("ok"):
                return CallResult("ok", value=msg.get("value"), seconds=self._elapsed(cid))
            return CallResult("error", error=str(msg.get("error")), seconds=self._elapsed(cid))

    def request_stop(self, cid: int | None) -> None:
        if cid is not None:
            self._write({"id": cid, "method": "__stop__"})

    def confirm_stopped(self, cid: int | None, deadline: float) -> bool:
        """After request_stop: wait for the stopped call to end; kill the process if it does not."""
        if cid is None:
            return True
        if self.wait(cid, deadline).status in ("error", "ok"):
            return True
        self.kill()
        return False

    def _elapsed(self, cid: int) -> float:
        return time.monotonic() - self._sent.get(cid, time.monotonic())

    def kill(self) -> None:
        self.killed = True
        if self._proc and self._proc.poll() is None:
            self._proc.kill()

    def close(self) -> None:
        if self._proc:
            self.kill()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            for f in (self._proc.stdin, self._proc.stdout):
                try:
                    if f is not None:
                        f.close()
                except OSError:
                    pass
            self._log.close()
            self._proc = None
