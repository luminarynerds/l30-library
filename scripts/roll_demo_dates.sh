#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# roll_demo_dates.sh - Keeps demo data fresh by rolling expired dates forward
# Runs weekly via cron. Calculates the minimum number of 7-day increments needed
# to bring each expired date into the future.

set -euo pipefail

CONTAINER="l30-database"
DB_USER="l30"
DB_NAME="l30_library"
LOG_FILE="/opt/l30/logs/roll_demo_dates.log"

# Demo-instance guard: this script resurrects past events forever, which is
# correct for a demo catalog and data corruption for a real library. It only
# runs when the operator has explicitly marked the install as a demo
# (touch /opt/l30/.demo_mode). Delete the marker at go-live.
DEMO_MARKER="/opt/l30/.demo_mode"
if [ ! -f "$DEMO_MARKER" ]; then
    mkdir -p /opt/l30/logs
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $DEMO_MARKER not found; not a demo instance, refusing to roll dates" >> "$LOG_FILE"
    exit 0
fi

mkdir -p /opt/l30/logs

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

run_sql() {
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "$1"
}

log "Starting demo date roll-forward"

# Roll events forward: add enough 7-day increments to land in the future
EVENTS_UPDATED=$(run_sql "
    UPDATE events
    SET start_time = start_time + (INTERVAL '7 days' * CEIL(EXTRACT(EPOCH FROM (NOW() - start_time)) / 604800)),
        end_time = end_time + (INTERVAL '7 days' * CEIL(EXTRACT(EPOCH FROM (NOW() - start_time)) / 604800)),
        updated_at = NOW()
    WHERE start_time < NOW();
" 2>&1)
EVENTS_COUNT=$(echo "$EVENTS_UPDATED" | grep -oP '\d+' | head -1)
EVENTS_COUNT=${EVENTS_COUNT:-0}
log "Events rolled forward: $EVENTS_COUNT rows"

# Roll programs forward: add enough 7-day increments to land in the future
PROGRAMS_UPDATED=$(run_sql "
    UPDATE programs
    SET program_date = program_date + (INTERVAL '7 days' * CEIL(EXTRACT(EPOCH FROM (NOW() - program_date::timestamp)) / 604800)),
        updated_at = NOW()
    WHERE program_date < NOW()::date;
" 2>&1)
PROGRAMS_COUNT=$(echo "$PROGRAMS_UPDATED" | grep -oP '\d+' | head -1)
PROGRAMS_COUNT=${PROGRAMS_COUNT:-0}
log "Programs rolled forward: $PROGRAMS_COUNT rows"

# Roll program_sessions forward if any have expired
SESSIONS_UPDATED=$(run_sql "
    UPDATE program_sessions
    SET session_date = session_date + (INTERVAL '7 days' * CEIL(EXTRACT(EPOCH FROM (NOW() - session_date::timestamp)) / 604800))
    WHERE session_date < NOW()::date;
" 2>&1)
SESSIONS_COUNT=$(echo "$SESSIONS_UPDATED" | grep -oP '\d+' | head -1)
SESSIONS_COUNT=${SESSIONS_COUNT:-0}
log "Program sessions rolled forward: $SESSIONS_COUNT rows"

log "Done. Events: $EVENTS_COUNT, Programs: $PROGRAMS_COUNT, Sessions: $SESSIONS_COUNT"
