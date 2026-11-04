"""Client for the Ping model server (sandbox/). Stdlib only (Pydantic optional).

Harnesses use this during the broadcast and action-submission windows. It
is part of the harness_api package, so there is nothing to copy:

    from typing import Literal
    from pydantic import BaseModel, Field
    from harness_api import LLMClient

    class Plan(BaseModel):
        action: str = Field(max_length=300)    # bound strings so output always ends fast

    llm = LLMClient()                          # the URL comes from PING_LLM_URL (see below)
    llm.generate("A giant is in the tavern.", system="You are a rogue.")      # -> str
    llm.generate("A giant is in the tavern.", schema=Plan)                    # -> Plan
    llm.short_text("Rally your allies in one line.", max_chars=150)          # -> str
    llm.choose("Which attribute fits 'pick the lock'?", ["strength", "dexterity"])  # -> one option
    llm.yes_no("Is a bronze-masked figure the same as 'a man in a bronze mask'?")    # -> bool

Every call takes `timeout=` (seconds): keep it inside the time limit of the window you are in
(harness_api.limits), so a slow answer can never make your submission late. A call that runs
out of time raises `Timeout`, and the server stops generating for it. The server also has its
own limit per request (30 s).

Which server: `LLMClient()` uses the PING_LLM_URL environment variable, or
http://127.0.0.1:8080 (the build-phase server from `./llm.sh up`) when it is not set. In the
real game the organisers set PING_LLM_URL to your player's own server, so do not hard-code
a URL.
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any


class ContextFull(RuntimeError):
    """Output was cut off because prompt + output filled the context window."""


class Timeout(RuntimeError):
    """The request ran out of time: the call's `timeout`, or the server's own limit."""


class ServerUnavailable(RuntimeError):
    """The model server cannot be reached, or is still loading the model."""


DEFAULT_URL = "http://127.0.0.1:8080"


class LLMClient:
    def __init__(self, base_url: str | None = None, timeout: float = 600.0) -> None:
        """`timeout` is the default for every call, in seconds; pass `timeout=` to a call to
        give it its own."""
        base_url = base_url or os.environ.get("PING_LLM_URL") or DEFAULT_URL
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.last: dict = {}   # full response of the last generation (token counts, finish)

    # ------------------------------------------------------------------ the server

    def _call(self, method: str, path: str, body: dict | None = None,
              timeout: float | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base_url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        limit = self.timeout if timeout is None else timeout
        try:
            # The server sends nothing until the answer is complete, so this is the call's
            # total time. Closing the connection on timeout makes the server stop generating.
            with urllib.request.urlopen(req, timeout=limit) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                msg = json.load(e).get("error", str(e))
            except (ValueError, AttributeError):   # a body that is not the server's JSON
                msg = str(e)
            if e.code == 504:
                raise Timeout(msg) from None
            if e.code == 503:
                raise ServerUnavailable(msg) from None
            raise ValueError(f"{e.code}: {msg}") from None
        except (TimeoutError, socket.timeout):
            raise Timeout(f"no answer within {limit} s") from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                raise Timeout(f"no answer within {limit} s") from None
            raise ServerUnavailable(f"cannot reach {self.base_url}: {e.reason}") from None

    def health(self, timeout: float = 2.0) -> bool:
        """True when the server is up and its model is loaded."""
        try:
            return self._call("GET", "/health", timeout=timeout).get("ok") is True
        except (ServerUnavailable, Timeout, ValueError):
            return False

    def wait_until_ready(self, timeout: float = 60.0) -> bool:
        """Wait for the model to load (useful in __init__ during the build phase)."""
        deadline = time.monotonic() + timeout
        while not self.health(timeout=min(2.0, max(0.1, deadline - time.monotonic()))):
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.5)
        return True

    # ------------------------------------------------------------------ generation

    def generate(self, prompt: str, system: str | None = None, schema: Any = None,
                 temperature: float | None = None, seed: int | None = None,
                 timeout: float | None = None) -> Any:
        """Run one generation.

        schema: None -> returns str. A Pydantic model class -> returns an instance of it.
        A JSON Schema dict -> returns the parsed JSON.
        temperature: 0..2, default set by the server. seed: same request + same seed ->
        same answer. timeout: seconds for this call (default: the client's).
        Raises Timeout, ContextFull (schema only), ServerUnavailable or ValueError (bad request).
        """
        body: dict = {"prompt": prompt}
        if system is not None:
            body["system"] = system
        if temperature is not None:
            body["temperature"] = temperature
        if seed is not None:
            body["seed"] = seed
        model_cls = schema if hasattr(schema, "model_json_schema") else None
        if schema is not None:
            body["schema"] = model_cls.model_json_schema() if model_cls else schema
        self.last = resp = self._call("POST", "/generate", body, timeout=timeout)
        if schema is None:
            return resp["text"]
        if resp["finish"] != "stop":
            raise ContextFull(f"output cut off after {resp['output_tokens']} tokens")
        return model_cls.model_validate_json(resp["text"]) if model_cls else json.loads(resp["text"])

    def short_text(self, prompt: str, max_chars: int = 300, system: str | None = None,
                   **kwargs: Any) -> str:
        """A reply of at most `max_chars` characters. The limit is part of the grammar, so the
        model cannot ramble, and the call always ends quickly."""
        schema = {"type": "object", "additionalProperties": False, "required": ["text"],
                  "properties": {"text": {"type": "string", "minLength": 1, "maxLength": max_chars}}}
        return str(self.generate(prompt, system=system, schema=schema, **kwargs)["text"]).strip()

    def choose(self, prompt: str, options: Sequence[str], system: str | None = None,
               **kwargs: Any) -> str:
        """Exactly one of `options`, picked by the model (the grammar allows nothing else)."""
        if not options:
            raise ValueError("choose() needs at least one option")
        schema = {"type": "object", "additionalProperties": False, "required": ["choice"],
                  "properties": {"choice": {"enum": list(options)}}}
        return str(self.generate(prompt, system=system, schema=schema, **kwargs)["choice"])

    def yes_no(self, question: str, system: str | None = None, **kwargs: Any) -> bool:
        """The model's yes/no answer to `question`."""
        return self.choose(question + "\nAnswer yes or no.", ["yes", "no"], system=system, **kwargs) == "yes"
