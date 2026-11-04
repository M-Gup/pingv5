"""Connects a harness in its sandbox to the game's server (organiser-side; , §14).

In the real game each player's container runs:

    python -m harness_api.client my_harness.py

with PING_GM_URL (for example ws://gm:9000/play) set by the organisers. The bridge sends the
NETID the submission declares (`NETID = "..."` on its Harness subclass), read from the file
without running it (harness_api/netid.py); the server refuses a NETID that is not on its
list, is blocked, or does not play in this run (403 Forbidden). The bridge runs the submission exactly like a local game does, in its own
process with harness_api/runner.py, and passes the game's calls to it over a WebSocket
(engine/server.py describes the frames). The time limits are measured on the game's side; a
call that overruns is stopped inside the runner, and if the game closes the connection the
runner is ended.

The submission's process gets a copy of the environment without PING_GM_URL. Its printed output goes to this container's stderr and is
forwarded to the organisers' log for that player.

Every message and event is one line on this container's stdout, in the same format as the
game's server (harness_api/eventlog.py, rich): each call from the game with a summary of its
message, each reply with its latency, the harness's printed output, and connection events.

Needs the `websockets` and `rich` packages: pip install "ping-harness[client]" (already in the
harness image). Participants do not need it to build or check a harness.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from harness_api.netid import is_valid, read_netid

RUNNER = Path(__file__).resolve().parent / "runner.py"
MAX_FRAME_BYTES = 1_000_000
MAX_LOG_LINE = 2000


def run(submission: Path, url: str, netid: str) -> int:
    from websockets.exceptions import InvalidStatus
    from websockets.sync.client import connect

    from harness_api.eventlog import EventLog

    log = EventLog("client")
    log.event(netid, None, "connecting", f"{url} · {submission.name}")
    try:
        with connect(url, additional_headers={"X-NetID": netid},
                     max_size=MAX_FRAME_BYTES, open_timeout=15) as ws:
            return _bridge(ws, submission, url, netid, log)
    except InvalidStatus as e:
        status = e.response.status_code
        why = "this NETID is not allowed, is blocked, or does not play in this run" if status == 403 else ""
        log.event(netid, None, f"refused ({status})", why, "error")
        return 1
    except (OSError, TimeoutError) as e:
        log.event(netid, None, "cannot connect", f"{type(e).__name__}: {e}", "error")
        return 1


def _bridge(ws, submission: Path, url: str, netid: str, log) -> int:
    from websockets.exceptions import ConnectionClosed

    env = {k: v for k, v in os.environ.items() if k != "PING_GM_URL"}
    log.event(netid, None, "connected", url)
    state: dict = {"cls": None, "pending": {}}       # class once known; call id -> (method, start)
    proc = subprocess.Popen([sys.executable, "-I", str(RUNNER), str(submission)], env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdin, stdout, stderr = proc.stdin, proc.stdout, proc.stderr
    assert stdin is not None and stdout is not None and stderr is not None

    def replies() -> None:            # runner -> game: one JSON reply per line
        for raw in stdout:
            line = raw.decode("utf-8").rstrip("\n")
            try:
                msg = json.loads(line)
                method, started = state["pending"].pop(msg.get("id"), (None, None))
                log.replied(netid, state["cls"], method, msg,
                            time.monotonic() - started if started is not None else None)
            except (ValueError, AttributeError, TypeError):
                pass
            try:
                ws.send(line)
            except ConnectionClosed:
                break
        log.event(netid, state["cls"], "harness process ended", f"exit code {proc.wait()}", "warn")
        ws.close()                    # the harness process ended: leave the game

    def output() -> None:             # the harness's print() output -> organisers' log
        for raw in stderr:
            line = raw.decode("utf-8", errors="replace")
            log.output(netid, state["cls"], line.rstrip("\n"))
            try:
                ws.send(json.dumps({"log": line[:MAX_LOG_LINE]}))
            except ConnectionClosed:
                pass

    threading.Thread(target=replies, daemon=True).start()
    threading.Thread(target=output, daemon=True).start()
    code = 0
    try:
        for frame in ws:              # game -> runner: calls and stop requests
            text = frame if isinstance(frame, str) else frame.decode()
            try:
                call = json.loads(text)
                arg = call.get("arg")
                if isinstance(arg, dict) and arg.get("type") == "initial_state":
                    state["cls"] = arg.get("your_class")
                if call.get("method") != "__stop__":
                    state["pending"][call.get("id")] = (call.get("method"), time.monotonic())
                log.sent(netid, state["cls"], call)
            except (ValueError, AttributeError):
                pass
            try:
                stdin.write(text.encode() + b"\n")
                stdin.flush()
            except OSError:
                break
    except ConnectionClosed:
        pass
    finally:
        if ws.close_code not in (None, 1000):
            log.event(netid, state["cls"], f"disconnected ({ws.close_code})", ws.close_reason or "", "error")
            code = 1
        else:
            log.event(netid, state["cls"], "disconnected", ws.close_reason or "game over")
        proc.kill()
        proc.wait(timeout=10)
    return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m harness_api.client", description=__doc__.split("\n\n")[0])
    ap.add_argument("submission", type=Path)
    ap.add_argument("--url", default=os.environ.get("PING_GM_URL"), help="default: $PING_GM_URL")
    args = ap.parse_args(argv)
    if not args.url:
        ap.error("set PING_GM_URL (or --url)")
    if not args.submission.is_file():
        ap.error(f"no such file: {args.submission}")
    netid = read_netid(args.submission)
    if netid is None or not is_valid(netid):
        ap.error(f'{args.submission} declares no valid NETID (add NETID = "your-netid" to its Harness class)')
    return run(args.submission.resolve(), args.url, netid)


if __name__ == "__main__":
    sys.exit(main())
