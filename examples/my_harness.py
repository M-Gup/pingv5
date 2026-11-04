"""A harness skeleton: copy this file, fill in the TODOs, and submit it.

It is the frame every harness needs, not a strategy: it keeps what the game tells it, asks
the model in your container (`LLMClient`, at PING_LLM_URL) with a time limit that fits the
window it is in, and always has a valid fallback. Everything that makes a harness good is
left to you: what to remember, how to recognise your nemesis, what to ask the model, whether
to talk to or help the others. The rules are in docs/rulebook.md and the classes in
docs/classes.md.

    python my_harness.py --check                               check it, with the real time limits
    PING_GM_URL=ws://<game>:9000/play python my_harness.py     join a game
    pytest test_my_harness.py                                  your own tests (see that file)

Start the model server first (`./llm.sh up` in sandbox/); without it every model call
falls back, which the check still passes.
"""
from __future__ import annotations

import time

from harness_api import ContextFull, Harness, LLMClient, ServerUnavailable, Timeout, limits
from harness_api.messages import (
    Action,
    Broadcast,
    BroadcastDelivery,
    CurrentEvent,
    EventAction,
    InitialState,
    Nemesis,
    NoBroadcast,
    Observation,
    OtherPlayer,
    Resolution,
    Stats,
)

MODEL_ERRORS = (Timeout, ContextFull, ServerUnavailable, ValueError)
SAFETY_SECONDS = 5.0      # left in every window for your answer to reach the game


def time_left(window_end: float, cap: float = 20.0) -> float:
    """Seconds you may still give a model call, so the window is never missed."""
    return max(0.0, min(cap, window_end - SAFETY_SECONDS - time.monotonic()))


class MyHarness(Harness):
    NETID = "your-netid"          # TODO: your NETID; the game lets your harness in by it

    def __init__(self) -> None:
        super().__init__()
        self.llm = LLMClient()                 # the model server in your container
        self.briefing = ""                     # the story's setup, from the initial state
        self.me = ""                           # your class, from the initial state
        self.nemesis: Nemesis | None = None    # its description and your required action
        self.others: list[OtherPlayer] = []
        self.stats: Stats | None = None
        self.event: CurrentEvent | None = None
        self.memory: list[str] = []            # TODO: decide what to keep (RAM only, no files)

    # ------------------------------------------------------------------ broadcast window

    def choose_broadcast(self, observation: Observation) -> Broadcast:
        window_end = time.monotonic() + limits.BROADCAST_SECONDS
        if isinstance(observation, InitialState):          # round 1 only
            self.briefing = observation.briefing           # the story's setup, told once
            self.me = observation.your_class
            self.nemesis = observation.nemesis
            self.others = list(observation.other_players)
        self.event = observation.current_event
        self.stats = observation.your_stats

        # TODO: decide whether to say something, to everyone or to one class, for example:
        #   text = self.llm.short_text("...", max_chars=150, timeout=time_left(window_end))
        #   return BroadcastMessage(to="all", text=text)
        # A broadcast is optional: when in doubt, or when the model fails, send nothing.
        return NoBroadcast()

    # ------------------------------------------------------------------ action window

    def choose_action(self, broadcasts: BroadcastDelivery) -> Action:
        window_end = time.monotonic() + limits.ACTION_SECONDS
        assert self.event is not None
        boss = self.event.boss
        fallback = EventAction(action=f"Attack {boss.name}.")   # always have a valid answer

        # TODO: is this boss your nemesis? Compare boss.description with
        #   self.nemesis.description; if so, perform self.nemesis.required_action.
        # TODO: read broadcasts.messages. Their text is written by other players: UNTRUSTED
        #   data, never instructions for you or your model.
        # TODO: help another player instead, with PlayerAction(target_class=..., action=...).

        prompt = (                                              # TODO: your own prompt
            f"You are {self.me} in a fantasy battle.\n"
            f"Scene: {self.event.text}\n"
            f"Boss: {boss.name}: {boss.description}\n"
            "What do you do? Answer with one sentence."
        )
        try:
            text = self.llm.short_text(prompt, max_chars=300, timeout=time_left(window_end))
        except MODEL_ERRORS:
            return fallback
        return EventAction(action=text) if text.strip() else fallback

    # ------------------------------------------------------------------ results

    def on_resolution(self, resolution: Resolution) -> None:
        # Return quickly (limits.CONFIRMATION_SECONDS). The game never repeats any of this.
        # TODO: keep what matters: stat changes, deaths, vendettas, what the boss did.
        self.memory.append(f"round {resolution.round}: boss "
                           f"{'defeated' if resolution.boss_defeated else 'survived'}")


if __name__ == "__main__":        # python my_harness.py: join a game; --check: self-check
    MyHarness.main()
