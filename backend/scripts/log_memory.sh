#!/usr/bin/env bash
# L30 memory snapshot logger — every 15 min via root cron.
# Restored 2026-06-13: the prior file was empty, so the morning OOM crash went unrecorded.
LOG=/var/log/l30-memory.log
# self-rotate so the logger never fills the disk
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || echo 0)" -gt 20971520 ]; then
  mv -f "$LOG" "$LOG.1"
fi
{
  echo "===== $(date -u '+%Y-%m-%d %H:%M:%S UTC') ====="
  free -h
  echo "-- swap --"; swapon --show 2>/dev/null || true
  echo "-- top 15 by RSS --"
  ps -eo pid,user,rss,vsz,etime,comm --sort=-rss 2>/dev/null | head -16
  echo "-- python/node inference procs (likely OOM culprits) --"
  ps -eo pid,user,rss,etime,args --sort=-rss 2>/dev/null | grep -E 'python|node|gunicorn|uvicorn|scraper' | grep -v grep | head -12
} >> "$LOG" 2>&1
