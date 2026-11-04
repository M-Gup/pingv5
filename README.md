# Ping: Dungeons & Dragons — AI Hackathon

Welcome to **Ping: Dungeons & Dragons**!

In this hackathon, you will build an **autonomous AI harness** (a Python class that interfaces with a language model) that plays a cooperative D&D-style campaign against formidable bosses. Your agent will be assigned one of 5 fantasy character classes, uncover its secret nemesis, coordinate with teammates, and fight to survive through all encounters.

---

## Quickstart (Get Running in 5 Minutes)

### Start the Local Model Server

Your harness communicates with a local **Llama-3.2-1B-Instruct** model running inside Docker.

```bash
docker run -d --rm --name pingv5 -p 127.0.0.1:8080:8080 ghcr.io/lg28literconvectionmicrowaveoven/pingv5:latest
```

### Run the Harness

```bash
PING_WS_URL=https://pingv5.snioe.dev uv run <harness.py>
```

---

---

## How to Build Your Harness

Open [`template/starter_harness.py`](template/starter_harness.py) (or [`examples/my_harness.py`](examples/my_harness.py)).

### 1. Set Your NetID

Every harness must declare your university NetID:

```python
class ParticipantHarness(Harness):
    NETID = "your-netid"  # Replace with your NetID
```

### 2. Implement the 3 Required Methods

| Method                 | When It Runs   | What You Receive                                      | What You Return                                           | Time Limit |
| :--------------------- | :------------- | :---------------------------------------------------- | :-------------------------------------------------------- | :--------- |
| **`choose_broadcast`** | Start of round | `InitialState` (Round 1) or `TurnMessage` (Rounds 2+) | `BroadcastMessage` (to all/class) or `NoBroadcast()`      | 30s        |
| **`choose_action`**    | Action window  | `BroadcastDelivery` (messages from teammates)         | `EventAction` (attack boss) or `PlayerAction` (buff ally) | 45s        |
| **`on_resolution`**    | End of round   | `Resolution` (damage, boss defeat, vendettas, deaths) | Return nothing (confirms receipt)                         | 5s         |

---

## Verification & Testing Commands

```bash
pytest examples/test_my_harness.py
```
