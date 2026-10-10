#!/usr/bin/env bash
#
# watch-api-contract.sh
#
# Watches backend/docs/api-contract.md and, whenever it changes, runs the
# `api-contract-sync` opencode agent to bring the frontend back in line with the
# contract. No prompt from you is required.
#
# On start it also syncs immediately if the contract differs from the last
# successful sync, so edits made before the watcher started are not missed.
#
# Usage:
#   scripts/watch-api-contract.sh start    # start in the background (default)
#   scripts/watch-api-contract.sh stop     # stop the background watcher
#   scripts/watch-api-contract.sh status   # show whether it is running
#   scripts/watch-api-contract.sh run      # run in the foreground (Ctrl-C to stop)
#
# Config (env vars):
#   WATCH_INTERVAL     seconds between polls           (default 5)
#   WATCH_DEBOUNCE     seconds to wait for a save to settle before syncing (default 3)
#   WATCH_RETRY_DELAY  seconds to wait before retrying a failed sync (default 30)
#   WATCH_AGENT        opencode agent to run           (default api-contract-sync)
#   WATCH_MODEL        optional provider/model override for the agent
#   WATCH_CONTRACT     override the watched file       (default backend/docs/api-contract.md)
#   WATCH_STATE_DIR    override the state/log dir      (default .watch)
#
# Logs: .watch/sync.log   PID: .watch/watch.pid   Last synced hash: .watch/api-contract.sha256
#
set -uo pipefail

SELF="$(realpath "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "$SELF")/.." && pwd)"

CONTRACT="${WATCH_CONTRACT:-$REPO_ROOT/backend/docs/api-contract.md}"
STATE_DIR="${WATCH_STATE_DIR:-$REPO_ROOT/.watch}"
HASH_FILE="$STATE_DIR/api-contract.sha256"
PID_FILE="$STATE_DIR/watch.pid"
LOG_FILE="$STATE_DIR/sync.log"

INTERVAL="${WATCH_INTERVAL:-5}"
DEBOUNCE="${WATCH_DEBOUNCE:-3}"
RETRY_DELAY="${WATCH_RETRY_DELAY:-30}"
AGENT="${WATCH_AGENT:-api-contract-sync}"
MODEL="${WATCH_MODEL:-}"

TRIGGER_MSG="backend/docs/api-contract.md changed. Sync the frontend to match the contract exactly, following your agent instructions. If nothing needs to change, say so and change nothing."

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$CONTRACT" | awk '{print $1}'
  else
    shasum -a 256 "$CONTRACT" | awk '{print $1}'
  fi
}

run_sync() {
  local hash="$1"
  local args=(run --auto --agent "$AGENT" --dir "$REPO_ROOT")
  [ -n "$MODEL" ] && args+=(--model "$MODEL")
  echo "[watch] $(date -Is) syncing -> $hash; running agent '$AGENT'" >>"$LOG_FILE"
  {
    echo "===== $(date -Is) sync start (hash $hash) ====="
    if opencode "${args[@]}" "$TRIGGER_MSG"; then
      echo "===== $(date -Is) sync ok ====="
      return 0
    else
      echo "===== $(date -Is) sync FAILED (exit $?) ====="
      return 1
    fi
  } >>"$LOG_FILE" 2>&1
}

sync_if_changed() {
  local current last settled
  current="$(hash_file)"
  last="$(cat "$HASH_FILE" 2>/dev/null || true)"
  if [ "$current" != "$last" ]; then
    sleep "$DEBOUNCE"
    settled="$(hash_file)"
    if run_sync "$settled"; then
      printf '%s\n' "$settled" >"$HASH_FILE"
    else
      echo "[watch] $(date -Is) sync failed; retrying in ${RETRY_DELAY}s" >>"$LOG_FILE"
      sleep "$RETRY_DELAY"
    fi
  fi
}

watch_loop() {
  mkdir -p "$STATE_DIR"
  if ! command -v opencode >/dev/null 2>&1; then
    echo "[watch] ERROR: 'opencode' not found on PATH" >&2
    exit 1
  fi
  if [ ! -f "$CONTRACT" ]; then
    echo "[watch] ERROR: contract not found at $CONTRACT" >&2
    exit 1
  fi
  echo "[watch] watching $CONTRACT every ${INTERVAL}s (pid $$); agent=$AGENT" >>"$LOG_FILE"
  # Initial sync: if the contract has never been synced (no hash file) or has
  # changed since the last successful sync, sync now. This catches edits made
  # before the watcher started.
  sync_if_changed
  while true; do
    sleep "$INTERVAL"
    [ -f "$CONTRACT" ] || continue
    sync_if_changed
  done
}

case "${1:-start}" in
  start)
    mkdir -p "$STATE_DIR"
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "[watch] already running (pid $(cat "$PID_FILE"))"
      exit 0
    fi
    nohup "$SELF" run >/dev/null 2>&1 &
    echo $! >"$PID_FILE"
    echo "[watch] started (pid $(cat "$PID_FILE")); logs: $LOG_FILE"
    ;;
  stop)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill "$(cat "$PID_FILE")" && rm -f "$PID_FILE"
      echo "[watch] stopped"
    else
      rm -f "$PID_FILE"
      echo "[watch] not running"
    fi
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "[watch] running (pid $(cat "$PID_FILE"))"
    else
      echo "[watch] not running"
    fi
    ;;
  run)
    watch_loop
    ;;
  *)
    echo "usage: $0 {start|stop|status|run}" >&2
    exit 2
    ;;
esac
