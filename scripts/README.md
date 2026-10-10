# scripts

## watch-api-contract.sh

Watches `backend/docs/api-contract.md`. When it changes, it automatically runs
the `api-contract-sync` opencode agent to update the frontend so it matches the
contract. You do not need to prompt it.

On start it also syncs immediately if the contract differs from the last
successful sync, so edits made before the watcher started are not missed. It
remembers the last synced version in `.watch/api-contract.sha256`.

It only edits `frontend/` and never commits. All actions are logged to
`.watch/sync.log`.

### Commands

A short alias `watch-contract` is linked in `~/.local/bin`, so you can run either
`watch-contract ...` or `scripts/watch-api-contract.sh ...` from the repo.

```bash
watch-contract start    # start watching in the background
watch-contract stop     # stop the background watcher
watch-contract status   # show whether it is running
watch-contract run      # run in the foreground (Ctrl-C to stop)
```

`start` is the default: running `watch-contract` with no argument starts it.

### Watch it work

```bash
tail -f .watch/sync.log
```

### Run the sync once, by hand

```bash
opencode run --agent api-contract-sync "Sync the frontend to backend/docs/api-contract.md"
```

Add `--auto` to skip permission prompts, or `--model provider/model` to pick a
model.

### Configuration

Set these before `start` (or before `run`):

| Variable             | Default                        | Meaning                                   |
| -------------------- | ------------------------------ | ----------------------------------------- |
| `WATCH_INTERVAL`     | `5`                            | Seconds between polls                     |
| `WATCH_DEBOUNCE`     | `3`                            | Seconds to wait for a save to settle      |
| `WATCH_RETRY_DELAY`  | `30`                           | Seconds to wait before retrying a failed sync |
| `WATCH_AGENT`        | `api-contract-sync`            | opencode agent to run on change           |
| `WATCH_MODEL`        | (agent default)                | Provider/model override for the agent     |
| `WATCH_CONTRACT`     | `backend/docs/api-contract.md` | File to watch                             |
| `WATCH_STATE_DIR`    | `.watch`                       | Where to keep the pid, hash, and log      |

Example:

```bash
WATCH_INTERVAL=2 watch-contract start
```

### Notes

- The watcher runs as a normal background process. It stops when you stop it or
  when the machine reboots.
- Each change spends tokens, because it launches a fresh opencode agent.
- The agent is restricted: it can only edit `frontend/**` and only run read-only
  commands (`ls`, `cat`, `rg`, `git status`, `git diff`, `node --check`, etc.).

### Files

- `.watch/watch.pid` — pid of the running watcher.
- `.watch/api-contract.sha256` — hash of the last successfully synced contract.
- `.watch/sync.log` — log of every sync run.
