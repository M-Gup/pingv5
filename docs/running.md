# Running the game: commands

Every command is a `uv run` script (defined in `pyproject.toml` and `organiser/pyproject.toml`).
Run them from the repository after `uv sync`. Arguments after a command go to it, so
`uv run ping-server --help` lists its options.

| Command | Side | What it does |
| --- | --- | --- |
| `uv run ping-stack` | organiser | Redis + Celery worker + game server with the live GM (Gemini), all in one |
| `uv run ping-server` | organiser | the game server and lobby only; scripted GM unless `--gm live` |
| `uv run ping-worker` | organiser | one Celery worker for GM requests |
| `uv run ping-redis up/down/status` | organiser | a local Redis for Celery, in Docker |
| `uv run ping-game` | organiser | one local game with harness files as local processes |
| `uv run ping-llm up/down/build/push/game P/verify P` | both | the model server (`sandbox/llm.sh`) |
| `uv run ping-play my_harness.py` | player | join a game (same as `python my_harness.py`) |
| `uv run ping-check my_harness.py` | player | the self-check (same as `python my_harness.py --check`) |

The server's story folder (`--story`) decides the kind of game:

- **no `characters.toml` in it** (for example `story/test_story`): every player who connects gets a
  single-player game of their own, straight away, with a random class. At most 5 games per NETID
  (`--games-per-netid`).
- **with `characters.toml`** (for example `content`): players wait in the lobby until as many are
  connected as it has classes; they play one game together, one game at a time. One game per
  NETID by default.

Players are let in by NETID: copy `config/netids.example.toml` to `config/netids.toml` and list
them under `allowed` (`blocked` refuses someone; edits apply at once).

---

## 1. Test the organiser side: server + orchestrator + Celery + live GM

```sh
gcloud auth application-default login          # once: the GM's Google Cloud login
cp config/netids.example.toml config/netids.toml   # then add the NETIDs that may play

uv run ping-stack --story story/test_story --serve 127.0.0.1:9000
```

`ping-stack` starts Redis in Docker if the broker in `config/gm.toml` is local and down, starts a
Celery worker, checks the Google Cloud login, then runs the server with `--gm live`. Ctrl+C stops
the server, the worker and the Redis it started. Without the live GM (no Google Cloud, no Redis):

```sh
uv run ping-server --story story/test_story --serve 127.0.0.1:9000
```

Or the parts separately, each in its own terminal:

```sh
uv run ping-redis up
uv run ping-worker
uv run ping-server --story story/test_story --serve 127.0.0.1:9000 --gm live
```

Every game the server runs is logged under `logs/<start time>-<story>/` (gitignored; choose
another place with `--log-dir`): one folder per game with `game.jsonl` (everything),
`<class>.log` (each harness's output), `seats.json` and `result.json`, and `server.log`, a plain
copy of the server's log lines (connections, refusals, reloads, every message).

## 2. Test the player side: model server + harness

```sh
uv run ping-llm up                                   # the model server on http://127.0.0.1:8080
cp examples/my_harness.py my_harness.py              # the skeleton; set NETID, fill in the TODOs
uv run ping-check my_harness.py                      # or: python my_harness.py --check
uv run pytest examples/test_my_harness.py            # the skeleton's tests (copy them next to yours)
```

Join the server from section 1 (its NETID must be in `allowed`):

```sh
PING_GM_URL=ws://127.0.0.1:9000/play uv run python my_harness.py       # Git Bash
$env:PING_GM_URL = "ws://127.0.0.1:9000/play"; uv run python my_harness.py   # PowerShell
```

Both sides print one log line per message. `uv run ping-llm down` stops the model server.

Without the server, a single game on one machine:

```sh
uv run ping-game --story story/test_story --player medusa=my_harness.py
```

## 3. Production

**Game host (organisers).**

```sh
uv run ping-stack --story content --serve 127.0.0.1:9000     # behind nginx, see below
```

- The server listens on `127.0.0.1` only; nginx (`deploy/nginx/ping-gm.conf`) terminates HTTPS and
  passes `wss://<gm-host>/play` on to it. Players then use `PING_GM_URL=wss://<gm-host>/play`.
- Run Redis as a managed service (not the Docker one `ping-stack` starts for a local broker URL),
  set `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` to it, and start workers on Linux with
  `uv run ping-worker --concurrency N`: the prefork pool there enforces the GM time limits, which
  Windows' solo pool ignores. The rate limit (`config/gm.toml`) is per worker.
- Keep `config/netids.toml` on the host only (it is gitignored).

**Each player (in the real game, run by the organisers per player).**

```sh
uv run ping-llm game <player>      # the player's own model server, on an internal network only
uv run ping-llm verify <player>    # check its image and hardening before the run
```

The harness then runs in its own container on that player's network, with
`PING_LLM_URL=http://llm:8080` and `PING_GM_URL=wss://<gm-host>/play`, as
`python -m harness_api.client my_harness.py`. That form reads only the NETID from the file and
runs the submission nowhere but in its own process. The harness image is not built yet
(AGENTS.md §18).
