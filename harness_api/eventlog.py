"""One stdout line per request, message and connection event, the same on both sides.

Used by the game's WebSocket server (engine/server.py) and by the bridge in each harness
container (harness_api/client.py), with rich. Every line has the same columns:

    18:52:07.412  ->  ab1234  medusa      broadcast window  #2   round 1 · briefing · boss Boss A · hp 50
    18:52:08.630  <-  ab1234  medusa      broadcast window  #2   to all: "Stay together." · 1.22s

On both sides `->` is a message from the game to the harness, `<-` one from the harness to
the game, and
`**` a connection event (connected, refused with 403, disconnected, lists reloaded). Event names
follow gm/SERVER.md. Text written by players is added as plain text, never as rich markup, so
it cannot change the log's styling or fake a log line. Long text is cut short.

Needs the `rich` package (organiser tools; `ping-harness[client]` in the harness image).
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from rich.console import Console
from rich.text import Text

EVENTS = {
    "init": "start-up",
    "choose_broadcast": "broadcast window",
    "choose_action": "action window",
    "on_resolution": "action results",
    "__stop__": "stop (time limit)",
}
TEXT_CHARS = 90

_console = Console(soft_wrap=True, highlight=False)    # stdout; plain text when not a terminal
_lock = threading.Lock()


def _cut(text: Any, n: int = TEXT_CHARS) -> str:
    s = " ".join(str(text).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def describe_request(method: str, arg: Any) -> str:
    """A one-line summary of what the game sends with a call."""
    try:
        if method == "choose_broadcast":
            boss, hp = arg["current_event"]["boss"]["name"], arg["your_stats"]["hp"]
            if arg.get("type") == "initial_state":
                return f"round {arg['round']} · briefing as {arg['your_class']} · boss {_cut(boss, 40)} · hp {hp}"
            return f"round {arg['round']} · boss {_cut(boss, 40)} · hp {hp}"
        if method == "choose_action":
            msgs = arg["messages"]
            heard = "; ".join(f"{m['from']}→{m['audience']}: \"{_cut(m['text'], 40)}\"" for m in msgs[:3])
            more = f" (+{len(msgs) - 3} more)" if len(msgs) > 3 else ""
            return f"round {arg['round']} · {len(msgs)} broadcast(s)" + (f" · {heard}{more}" if msgs else "")
        if method == "on_resolution":
            parts = [f"round {arg['round']}", "boss defeated" if arg["boss_defeated"] else "boss survived",
                     f"{len(arg['stat_changes'])} stat change(s)"]
            if arg.get("vendetta_completed"):
                parts.append("vendetta: " + ", ".join(arg["vendetta_completed"]))
            if arg.get("deaths"):
                parts.append("deaths: " + ", ".join(arg["deaths"]))
            if arg.get("run_over"):
                parts.append("run over")
            return " · ".join(parts)
        return ""
    except (KeyError, TypeError, IndexError):
        return _cut(json.dumps(arg, default=str))


def describe_reply(method: str | None, msg: dict) -> str:
    """A one-line summary of a harness's reply to a call."""
    if msg.get("ok") is not True:
        return f"error: {_cut(msg.get('error'), 120)}"
    value: Any = msg.get("value")
    if not isinstance(value, dict):
        return "ok" if method in ("init", "on_resolution") else f"invalid value: {_cut(json.dumps(value, default=str))}"
    try:
        if method == "choose_broadcast":
            if value.get("to", "none") == "none":
                return "no broadcast"
            return f"to {value['to']}: \"{_cut(value.get('text', ''))}\""
        if method == "choose_action":
            if value.get("target") == "player":
                return f"help {value.get('target_class')}: \"{_cut(value.get('action', ''))}\""
            return f"event: \"{_cut(value.get('action', ''))}\""
        return "ok"
    except (AttributeError, TypeError):
        return f"invalid value: {_cut(json.dumps(value, default=str))}"


class EventLog:
    """Writes the lines. `side` is "server" or "client" (only for the first line's banner)."""

    def __init__(self, side: str, console: Console | None = None):
        self.side = side
        self.console = console or _console
        self._files: list[Console] = []

    def also_to(self, path) -> None:
        """Also append every line, as plain text, to the file at `path` (for example the
        server's logs/<run>/server.log)."""
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        f = open(path, "a", encoding="utf-8", buffering=1)
        self._files.append(Console(file=f, soft_wrap=True, highlight=False, color_system=None,
                                   force_terminal=False, width=10_000))

    def _line(self, arrow: str, arrow_style: str, netid: str | None, cls: str | None,
              event: str, cid: Any, detail: str, detail_style: str = "") -> None:
        now = time.time()
        line = Text()
        line.append(time.strftime("%H:%M:%S", time.localtime(now)) + f".{int(now * 1000) % 1000:03d}  ", "dim")
        line.append(f"{arrow:<3} ", arrow_style)
        line.append(f"{(netid or '-')[:12]:<12} ", "bold cyan")
        line.append(f"{(cls or '-')[:13]:<13} ", "magenta")
        line.append(f"{event[:18]:<18} ", "yellow")
        line.append(f"{('#' + str(cid)) if cid is not None else '':<5} ", "dim")
        line.append(detail, detail_style)          # plain text: player text is never markup
        with _lock:
            self.console.print(line)
            for f in self._files:
                f.print(line)

    def sent(self, netid: str | None, cls: str | None, frame: dict) -> None:
        """A frame from the game to a harness."""
        method = str(frame.get("method"))
        self._line("->", "green", netid, cls, EVENTS.get(method, method), frame.get("id"),
                   describe_request(method, frame.get("arg")))

    def replied(self, netid: str | None, cls: str | None, method: str | None, msg: dict,
                seconds: float | None = None) -> None:
        """A harness's reply to a call."""
        detail = describe_reply(method, msg) + (f" · {seconds:.2f}s" if seconds is not None else "")
        self._line("<-", "blue", netid, cls, EVENTS.get(method or "", method or "reply"), msg.get("id"),
                   detail, "" if msg.get("ok") is True else "red")

    def output(self, netid: str | None, cls: str | None, text: str) -> None:
        """A line the harness printed."""
        self._line("..", "dim", netid, cls, "harness output", None, _cut(text, 160), "dim")

    def event(self, netid: str | None, cls: str | None, what: str, detail: str = "",
              level: str = "info") -> None:
        """A connection event: connected, refused, disconnected, reloaded..."""
        style = {"info": "bold", "warn": "bold yellow", "error": "bold red"}[level]
        self._line("**", style, netid, cls, what, None, detail, {"info": "", "warn": "yellow", "error": "red"}[level])
