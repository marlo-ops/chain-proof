#!/usr/bin/env bash
# reproduce.sh — prove Marlo's log is intact, and prove the checker can fail.
#
#   1. verify the live log
#   2. tamper a copy and confirm the checker catches it (a checker that never
#      fails proves nothing)
#   3. emit a compact, quotable anchor for the verified log
set -euo pipefail
cd "$(dirname "$0")"

LOG="${1:-../../log/events.jsonl}"

echo "== 1. verify $LOG =="
python3 chainproof.py "$LOG"
echo

echo "== 2. self-test: a tampered copy MUST fail =="
tmp="$(mktemp)"
cp "$LOG" "$tmp"
# change one hashed field on line 1 without touching id/hash
sed -i '1s/"trust":"trusted"/"trust":"untrusted"/' "$tmp"
if python3 chainproof.py "$tmp" >/dev/null 2>&1; then
  echo "SELFTEST FAILED: tampering was NOT detected"; rm -f "$tmp"; exit 1
fi
echo "OK: tampering detected (checker can fail)"
rm -f "$tmp"
echo

echo "== 3. anchor (save as anchor.json) =="
python3 chainproof.py "$LOG" --anchor | tee anchor.json
