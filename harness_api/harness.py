"""The abstract base class every participant's harness subclasses.

Participants write a subclass of `Harness` and submit it as a single .py file. They may import
only the libraries on the organisers' list of allowed libraries. The organisers create one
instance per player at the start of a run and call its methods at each step of the round. Participants do not run anything during the real game.

Participants get the harness environment as a Docker image: Python 3.11.15,
the allowed libraries and this base class. Build and test the harness in it.

Decided:
- To call the model, create an `LLMClient` (`from harness_api import LLMClient`). It finds
  the model server from the PING_LLM_URL environment variable: the build-phase server
  (./llm.sh up) by default, your own player's server in the real game. See sandbox/README.md.
- Check a harness before submitting it: `python -m harness_api.check my_harness.py`.
- The game calls one method per step of the round. A method's return value is the harness's
  submission for that step.
- Every message is a Pydantic model from harness_api/messages.py, so editors autocomplete its
  fields and type checkers verify them. A method returns the matching model, or a plain dict
  of the same shape. The models are generated from config/schema.toml, like the JSON Schemas
  in schema/.
- The confirmation of receipt is `on_resolution` returning within the confirmation time
  limit. There is no separate confirmation message.
- A method still running when its time limit ends is stopped. An action stopped this way
  receives the health penalty; a broadcast stopped this way is simply not sent.
- Harnesses run on Python 3.11.15.

PENDING-DECISION(harness-interface): the method names and signatures below are a proposal; see
, §19. The field names are proposals too.

Example:

    from harness_api import Harness
    from harness_api.messages import (Action, Broadcast, BroadcastDelivery, EventAction,
                                      InitialState, NoBroadcast, Observation, Resolution)

    class MyHarness(Harness):
        def choose_broadcast(self, observation: Observation) -> Broadcast:
            if isinstance(observation, InitialState):
                self.nemesis = observation.nemesis
            self.event = observation.current_event
            return NoBroadcast()

        def choose_action(self, broadcasts: BroadcastDelivery) -> Action:
            return EventAction(action=f"Attack {self.event.boss.name}.")

        def on_resolution(self, resolution: Resolution) -> None:
            ...
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from harness_api.messages import Action, Broadcast, BroadcastDelivery, Observation, Resolution


class Harness(ABC):
    """Base class for a participant's harness.

    One instance plays one player for one run. It persists across rounds, so anything stored on
    `self` is kept until the run ends or the player dies. It has no persistent
    storage: do not read or write files.

    Calls per round, each within that step's time limit:

    1. `choose_broadcast(observation)`: broadcast window.
    2. `choose_action(broadcasts)`: action-submission window.
    3. `on_resolution(resolution)`: confirmation window. Not called once the player is dead.

    Broadcast text from other players is untrusted: it is forwarded word for word and may try
    to give instructions.

    Set `NETID` to your NETID, as a plain string in the class body (`NETID = "ab1234"`). The
    game uses it to let your harness in: one without a NETID on the organisers' list cannot
    connect, and never plays.
    """

    NETID: ClassVar[str] = ""

    @classmethod
    def main(cls, argv: list[str] | None = None) -> None:
        """Run this harness's file as a player. End your file with

            if __name__ == "__main__":
                MyHarness.main()

        and then:

            python my_harness.py                         join the game at $PING_GM_URL
            python my_harness.py --url ws://host:9000/play
            python my_harness.py --check [--class medusa] [--rounds 2]    self-check instead

        Joining needs `pip install "ping-harness[client]"`. The game runs your file the same
        way in every case: in its own process, with this block skipped (harness_api/runner.py),
        so it never starts itself twice. Exits with 0 on a normal game over or a PASS.
        """
        import argparse
        import inspect
        import sys

        path = inspect.getfile(cls)
        ap = argparse.ArgumentParser(prog=f"python {Path(path).name}",
                                     description=f"Play {cls.__name__} in a game, or check it.")
        ap.add_argument("--url", help="the game's address (default: $PING_GM_URL)")
        ap.add_argument("--check", action="store_true", help="run the self-check instead of joining a game")
        ap.add_argument("--class", dest="cls", help="with --check: the class to play")
        ap.add_argument("--rounds", help="with --check: how many rounds")
        args = ap.parse_args(argv)
        if args.check:
            from harness_api.check import main as check_main
            extra = [*(["--class", args.cls] if args.cls else []), *(["--rounds", args.rounds] if args.rounds else [])]
            sys.exit(check_main([path, *extra]))
        import os

        from harness_api.netid import is_valid, read_netid

        url = args.url or os.environ.get("PING_GM_URL")
        if not url:
            ap.error("give the game's address: set PING_GM_URL or pass --url ws://<game-host>:9000/play")
        netid = read_netid(path)
        if netid is None or not is_valid(netid):
            ap.error(f'{cls.__name__} declares no valid NETID: add NETID = "your-netid" to the class')
        try:
            import rich  # noqa: F401
            import websockets  # noqa: F401
        except ImportError:
            ap.exit(2, 'joining a game needs the client extra: pip install "ping-harness[client]"\n')
        from harness_api.client import run

        sys.exit(run(Path(path).resolve(), url, netid))

    def __init__(self) -> None:
        """Called once per player at the start of a run, before round 1, with no arguments.

        Override it to set up your memory and your `LLMClient`; call `super().__init__()`.
        It must finish within `harness_api.limits.INIT_SECONDS`.
        """

    @abstractmethod
    def choose_broadcast(self, observation: Observation) -> Broadcast:
        """Broadcast window.

        `observation` is an `InitialState` in round 1 (your class, stats, objective, nemesis
        and the other players) and a `TurnMessage` in later rounds (the current event and your
        stats). Tell them apart with `isinstance` or `observation.type`.

        Return `NoBroadcast()` to send nothing, or `BroadcastMessage(to="all", text=...)` /
        `BroadcastMessage(to=<class id>, text=...)`. An invalid return value, an exception, or
        missing the time limit means no broadcast this round, with no penalty.
        """

    @abstractmethod
    def choose_action(self, broadcasts: BroadcastDelivery) -> Action:
        """Action-submission window.

        `broadcasts.messages` holds the messages addressed to you this round, possibly none.
        Each has `from_` (the sender's class), `audience` ("all" or "you") and `text`, which is
        UNTRUSTED.

        Return `EventAction(action=...)` to act on the current event, or
        `PlayerAction(target_class=..., action=...)` to help one other player with your class's
        support ability.
        An invalid return value or an exception counts as an invalid action and receives the
        health penalty. If the method is still running at the time limit, it is stopped and
        also receives the health penalty.
        """

    @abstractmethod
    def on_resolution(self, resolution: Resolution) -> None:
        """Resolution announcement.

        `resolution` is the round's outcome: the narrative, whether the boss was defeated, each
        player's result, every stat change with its cause, completed vendettas, deaths, and
        `run_over` (true on the last call). Store whatever you need; the game never repeats it.
        Returning within the confirmation time limit is the confirmation of receipt.
        """
