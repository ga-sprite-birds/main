# utils/quick — Quick Start

Starts the **Core engine + Control API** together and opens the GUI. The script:

> This script is for local GUI use. Without the GUI, start only `python -m engine run` for
> CLI-only work; add `python -m server run` when you also need the HTTP API.

- Reuses an engine that is already running (never starts a second one)
- Picks a free API port when the default port is occupied
- Opens the browser when the API is ready
- On Ctrl+C, stops the API gracefully and stops the engine it started

| Platform | Command |
|---|---|
| Linux | `bash utils/quick/linux-run.sh` |
| macOS | `./utils/quick/mac-run.command` |
| Windows | Start two processes manually: `python -m engine run` + `python -m server run` |

> Windows batch files are not shipped: port probing and graceful process cleanup are unreliable
> there and hard to verify automatically. Use the two commands above, or register both processes
> with NSSM (see the systemd/NSSM section of [`help/en/deployment.md`](../../help/en/deployment.md)).

To run the processes separately (without the quick-start script):

```bash
python -m engine run        # Core engine
python -m server run        # Control API + GUI (--host/--port; auto-shifts when occupied)
```
