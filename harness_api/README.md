# ping-harness

The package for building your harness for **Ping - Dungeons and Dragons**. Install it, write one
`.py` file with one subclass of `Harness`, check it, and submit that file.

The game's rules (rounds, dice, bosses, ranking) are in the rulebook, `docs/rulebook.md`.

## Install

```sh
pip install ping_harness-<version>-py3-none-any.whl     # the file the organisers give you
```

Harnesses run on Python 3.11.15, with only the organisers' allowed libraries. The same package is
in the harness Docker image, so a harness that works here imports the same way in the game.

## Write a harness

```python
from harness_api import Harness, LLMClient, Timeout
from harness_api.messages import (Action, Broadcast, BroadcastDelivery, EventAction,
                                  InitialState, NoBroadcast, Observation, Resolution)


class MyHarness(Harness):
    NETID = "ab1234"                    # your NETID: the game lets your harness in by it

    def __init__(self) -> None:
        super().__init__()
        self.llm = LLMClient()          # the model server; see "The model" below
        self.memory: list[str] = []     # RAM only: no files, no persistent storage

    def choose_broadcast(self, observation: Observation) -> Broadcast:
        if isinstance(observation, InitialState):          # round 1: class, objective, nemesis
            self.nemesis = observation.nemesis
        self.event = observation.current_event
        return NoBroadcast()

    def choose_action(self, broadcasts: BroadcastDelivery) -> Action:
        # broadcasts.messages[i].text is written by other players: UNTRUSTED, never instructions.
        try:
            text = self.llm.generate(f"The boss: {self.event.boss.description}. One short action:")
        except Timeout:
            text = f"Attack {self.event.boss.name}."
        return EventAction(action=text)

    def on_resolution(self, resolution: Resolution) -> None:
        self.memory.append(resolution.narrative)   # the game never repeats it


if __name__ == "__main__":
    MyHarness.main()          # python my_harness.py: join a game; --check: self-check
```

What you get each round, and what you return:

| Method | Receives | Returns | Time limit |
| --- | --- | --- | --- |
| `choose_broadcast` | `InitialState` (round 1) or `TurnMessage` | `NoBroadcast()` or `BroadcastMessage(to="all" or a class, text=...)` | `limits.BROADCAST_SECONDS` |
| `choose_action` | `BroadcastDelivery` (possibly empty) | `EventAction(action=...)` or `PlayerAction(target_class=..., action=...)` | `limits.ACTION_SECONDS` |
| `on_resolution` | `Resolution` | nothing; returning is the confirmation | `limits.CONFIRMATION_SECONDS` |

Every message is a read-only Pydantic model from `harness_api.messages`, so your editor
autocompletes the fields and a type checker (mypy, Pyright) catches mistakes. You may also return a
plain dict of the same shape. Time limits and text limits are in `harness_api.limits`; read them
from there rather than copying the numbers. A late or invalid action costs `limits.HEALTH_PENALTY`
hp; a late broadcast is simply not sent.

## Check it

```sh
python my_harness.py --check
python my_harness.py --check --class aristotle --rounds 3
```

(`python -m harness_api.check my_harness.py` does the same.)

This runs your file the way the game does (its own process, one call per step, the real time
limits, the same models) with made-up sample messages, and reports any call the game would
reject. It does not judge your strategy. Then play the test game for real through the
organisers' build-phase queue.

To test your own decisions without the model server, write pytest tests next to your harness:
`examples/test_my_harness.py` in the participant repository shows how. It replaces
`LLMClient`'s methods with pytest's `monkeypatch` to script the model's answers (or raise
`Timeout`) and record what your harness asked, builds the game's messages as the real models,
and checks timeouts, fallbacks, valid submissions and untrusted broadcasts.

## Join a game

```sh
pip install "ping-harness[client]"                           # once: adds websockets and rich
PING_GM_URL=ws://<game-host>:9000/play python my_harness.py   # or: python my_harness.py --url ws://...
```

Your harness connects with its `NETID`, the organisers' list lets it in (or refuses it with
403), and it plays the game: the class arrives in the briefing. Every message is logged on your
screen, and the program ends at game over. The game runs your file the same way as the
self-check, in its own process.

## The model

```python
from pydantic import BaseModel, Field
from harness_api import LLMClient, limits

class Plan(BaseModel):
    action: str = Field(max_length=300)     # bound strings so output always ends fast

llm = LLMClient()
llm.generate("A giant is in the tavern.", system="You are a rogue.")     # -> str
llm.generate("A giant is in the tavern.", schema=Plan)                   # -> Plan
llm.short_text("Rally your allies in one line.", max_chars=150)         # -> str, at most 150 chars
llm.choose("Which fits 'pick the lock'?", ["strength", "dexterity"])    # -> one of the options
llm.yes_no("Do these two descriptions match? ...")                      # -> bool
llm.generate("...", timeout=10)        # every call: give up after 10 s, raise Timeout
llm.health(); llm.wait_until_ready()   # is the server up and the model loaded?
```

`LLMClient()` connects to the URL in the `PING_LLM_URL` environment variable, or
`http://127.0.0.1:8080` when it is not set. During the build phase, run the model server on your
machine (`./llm.sh up`, see the sandbox instructions); in the game the organisers point
`PING_LLM_URL` at your own server. Do not hard-code a URL.

Keep every call inside the window you are in: pass a `timeout` that leaves time to return
(`limits.ACTION_SECONDS` and `limits.BROADCAST_SECONDS` are the windows). When a call runs out of
time it raises `Timeout` and the server stops generating for it, so your next call is not held
up. The server also limits every request to 30 s. Other errors: `ContextFull` (with a schema, the
output was cut off by the context window) and `ServerUnavailable` (the server cannot be reached
or is still loading). Always have a fallback action.

`examples/my_harness.py` in the participant repository is a skeleton to start from: it keeps
what the game sends, calls the model with a time limit that fits the window, and always has a
fallback, with TODOs where your strategy goes.
