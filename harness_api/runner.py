"""Runs one participant's harness in its own process (organiser-side; ).

Started by harness_api/process.py (for the orchestrator in engine/ or the self-check), one
process per player:

    python -I harness_api/runner.py path/to/submission.py

Protocol: one JSON object per line. The orchestrator writes requests to stdin:

    {"id": 1, "method": "init"}                         import the file, create the instance
    {"id": 2, "method": "choose_broadcast", "arg": {...}}
    {"id": 2, "method": "__stop__"}                     stop the running call (time limit)

and this runner answers each call on its own protocol channel:

    {"id": 2, "ok": true, "value": {...}}  or  {"id": 2, "ok": false, "error": "..."}

The harness's own print() output goes to stderr (the player's log), never to the protocol
channel. Each call runs in a worker thread; `__stop__` raises StopExecution inside it. That
stops Python code, but not a call blocked inside C (for example time.sleep or a socket
read); the orchestrator then kills the process.

Messages travel as JSON. Before each call the runner turns the message into its Pydantic
model from harness_api/messages.py; a returned model is turned back into JSON (a returned plain
dict is passed on as it is). The orchestrator validates every return value itself.

This runner does not enforce anything: the orchestrator measures every time limit itself.
Participants may read this file; it holds nothing organiser-only.
"""
from __future__ import annotations

import ctypes
import importlib.util
import inspect
import io
import json
import os
import sys
import threading
import traceback
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, TypeAdapter  # noqa: E402

from harness_api.harness import Harness  # noqa: E402
from harness_api.messages import BroadcastDelivery, Observation, Resolution  # noqa: E402

# How each method's message is turned into its model before the call.
METHODS: dict[str, Callable[[Any], Any]] = {
    "choose_broadcast": TypeAdapter(Observation).validate_python,
    "choose_action": BroadcastDelivery.model_validate,
    "on_resolution": Resolution.model_validate,
}


def to_json(value):
    """A returned model becomes its JSON form; anything else is passed on unchanged."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    return value


class StopExecution(BaseException):
    """Raised inside a call that overran its time limit. A BaseException, so that a
    harness's `except Exception:` does not swallow it."""


def load_harness_class(path: str) -> type[Harness]:
    spec = importlib.util.spec_from_file_location("submission", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path!r} as a Python module")
    module = importlib.util.module_from_spec(spec)
    sys.modules["submission"] = module
    spec.loader.exec_module(module)
    found = [
        c for c in vars(module).values()
        if inspect.isclass(c) and issubclass(c, Harness) and c.__module__ == "submission"
        and not inspect.isabstract(c)
    ]
    if len(found) != 1:
        raise TypeError(f"the submission must define exactly one concrete Harness subclass, found {len(found)}")
    return found[0]


def main() -> None:
    submission = sys.argv[1]
    # Keep the real stdout for the protocol; send everything else printed to stderr.
    channel = io.open(os.dup(1), "w", encoding="utf-8", newline="\n", buffering=1)
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    requests = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    write_lock = threading.Lock()
    state: dict = {"harness": None, "worker": None}

    def reply(msg: dict) -> None:
        with write_lock:
            channel.write(json.dumps(msg) + "\n")
            channel.flush()

    def run(req: dict) -> None:
        rid = req["id"]
        try:
            if req["method"] == "init":
                state["harness"] = load_harness_class(submission)()
                value = None
            elif req["method"] in METHODS and state["harness"] is not None:
                message = METHODS[req["method"]](req.get("arg"))
                value = to_json(getattr(state["harness"], req["method"])(message))
            else:
                raise RuntimeError(f"cannot call {req['method']!r} now")
            try:
                text = json.dumps({"id": rid, "ok": True, "value": value})
            except (TypeError, ValueError) as e:
                text = json.dumps({"id": rid, "ok": False, "error": f"return value is not JSON: {e}"})
            with write_lock:
                channel.write(text + "\n")
                channel.flush()
        except StopExecution:
            reply({"id": rid, "ok": False, "error": "stopped at the time limit"})
        except BaseException as e:  # noqa: BLE001 - any failure is reported, never fatal
            traceback.print_exc()
            reply({"id": rid, "ok": False, "error": f"{type(e).__name__}: {e}"})

    for line in requests:
        req = json.loads(line)
        worker = state["worker"]
        busy = worker is not None and worker.is_alive()
        if req["method"] == "__stop__":
            if busy:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(worker.ident),
                                                           ctypes.py_object(StopExecution))
            continue
        if busy:
            reply({"id": req["id"], "ok": False, "error": "the previous call is still running"})
            continue
        state["worker"] = threading.Thread(target=run, args=(req,), daemon=True)
        state["worker"].start()


if __name__ == "__main__":
    main()
