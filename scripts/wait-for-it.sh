#!/usr/bin/env bash
# wait-for-it.sh — block until a TCP host:port is reachable, then optionally exec.
# Slim, dependency-free rewrite of the classic vishnubob/wait-for-it.
#
# Usage:  wait-for-it.sh host:port [-t timeout] [-q] [-- command [args...]]

set -Eeuo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") host:port [-t timeout_seconds] [-q] [-- command ...]

  host:port        host and TCP port to probe
  -t, --timeout    seconds to wait before giving up (default 30, 0 = forever)
  -q, --quiet      suppress status messages
      --strict     only run the command after success (default)
  --               separator before the command to exec

Exit codes: 0 success · 1 invalid args · 124 timeout · 127 host unreachable
EOF
  exit 1
}

QUIET=0
TIMEOUT=30
HOST=
PORT=
CMD=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -q|--quiet)   QUIET=1;            shift ;;
    -t|--timeout) TIMEOUT="$2";       shift 2 ;;
    --strict)                         shift ;;
    --)           shift; CMD=("$@");  break ;;
    *:*)          HOST="${1%%:*}"; PORT="${1##*:}"; shift ;;
    -h|--help)    usage ;;
    *)            echo "unknown arg: $1" >&2; usage ;;
  esac
done

[[ -z "$HOST" || -z "$PORT" ]] && usage

log() { (( QUIET )) || printf '[wait-for-it] %s\n' "$*" >&2; }

start=$(date +%s)
while :; do
  if (echo > "/dev/tcp/${HOST}/${PORT}") >/dev/null 2>&1; then
    log "${HOST}:${PORT} is available after $(( $(date +%s) - start ))s"
    break
  fi
  if (( TIMEOUT > 0 )) && (( $(date +%s) - start >= TIMEOUT )); then
    log "timeout after ${TIMEOUT}s waiting for ${HOST}:${PORT}"
    exit 124
  fi
  sleep 1
done

if (( ${#CMD[@]} > 0 )); then
  exec "${CMD[@]}"
fi
