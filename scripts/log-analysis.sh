#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

# L30 Library Log Analysis Script
# Analyzes logs to find errors, trends, and anomalies
# Usage: ./log-analysis.sh [hours] [log-type]
# Example: ./log-analysis.sh 24 backend

set -e

# Configuration
PROJECT_DIR="/opt/l30"
LOG_DIR="$PROJECT_DIR/logs"
ANALYSIS_REPORT_DIR="$LOG_DIR/analysis"
HOURS="${1:-24}"  # Default to last 24 hours
LOG_TYPE="${2:-all}"  # all, backend, database, nginx, error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() {
  echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
  echo -e "${GREEN}[OK]${NC} $1"
}

info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

# Ensure directories exist
mkdir -p "$ANALYSIS_REPORT_DIR"

# Calculate time boundaries
CURRENT_TIME=$(date +%s)
START_TIME=$((CURRENT_TIME - HOURS * 3600))
START_DATE=$(date -d "@$START_TIME" +"%Y-%m-%d %H:%M:%S")
CURRENT_DATE=$(date +"%Y-%m-%d %H:%M:%S")

info "Analyzing logs from the last $HOURS hours"
info "Time range: $START_DATE to $CURRENT_DATE"
echo ""

# Function: Analyze backend logs
analyze_backend() {
  local log_file="$LOG_DIR/backend.log"

  if [ ! -f "$log_file" ]; then
    warning "Backend log file not found: $log_file"
    return
  fi

  echo "=== Backend Log Analysis ==="
  echo ""

  # Find errors from last N hours
  info "Finding errors in backend logs..."
  ERROR_COUNT=$(grep -ic "error\|exception\|failed" "$log_file" 2>/dev/null || echo "0")

  if [ "$ERROR_COUNT" -gt 0 ]; then
    warning "Found $ERROR_COUNT error-related lines in backend logs"
    echo ""

    # Show recent errors
    info "Most recent errors:"
    grep -i "error\|exception\|failed" "$log_file" 2>/dev/null | tail -10 | while read line; do
      echo "  $line"
    done
    echo ""
  else
    success "No errors found in backend logs"
  fi

  # Count warnings
  WARNING_COUNT=$(grep -ic "warning\|deprecated" "$log_file" 2>/dev/null || echo "0")
  if [ "$WARNING_COUNT" -gt 0 ]; then
    warning "Found $WARNING_COUNT warnings"
  fi

  # Error types breakdown
  info "Error type breakdown:"
  grep -io "error: [^,]*" "$log_file" 2>/dev/null | cut -d: -f2 | sort | uniq -c | sort -rn | head -10 | while read count type; do
    echo "  $type: $count occurrences"
  done
  echo ""
}

# Function: Analyze database logs
analyze_database() {
  local log_file="$LOG_DIR/database.log"

  if [ ! -f "$log_file" ]; then
    warning "Database log file not found: $log_file"
    return
  fi

  echo "=== Database Log Analysis ==="
  echo ""

  # Find database errors
  info "Finding database errors..."
  DB_ERROR_COUNT=$(grep -ic "error\|failed\|exception" "$log_file" 2>/dev/null || echo "0")

  if [ "$DB_ERROR_COUNT" -gt 0 ]; then
    warning "Found $DB_ERROR_COUNT database error-related lines"
    echo ""

    # Most common errors
    info "Most common database errors:"
    grep -i "error\|failed" "$log_file" 2>/dev/null | head -5 | while read line; do
      echo "  $line"
    done
    echo ""
  fi

  # Connection issues
  CONNECTION_ERRORS=$(grep -ic "connection\|refused\|timeout" "$log_file" 2>/dev/null || echo "0")
  if [ "$CONNECTION_ERRORS" -gt 0 ]; then
    warning "Found $CONNECTION_ERRORS connection-related errors"
  fi

  # Query performance
  info "Slow query analysis:"
  SLOW_QUERIES=$(grep -i "slow\|duration" "$log_file" 2>/dev/null | wc -l || echo "0")
  echo "  Slow queries detected: $SLOW_QUERIES"
  echo ""
}

# Function: Analyze Nginx logs
analyze_nginx() {
  local log_file="$LOG_DIR/nginx-access.log"

  if [ ! -f "$log_file" ]; then
    warning "Nginx log file not found: $log_file"
    return
  fi

  echo "=== Nginx Log Analysis ==="
  echo ""

  # HTTP status code distribution
  info "HTTP Status Code Distribution:"
  awk '{print $9}' "$log_file" 2>/dev/null | sort | uniq -c | sort -rn | while read count status; do
    case $status in
      2*) echo "  $status: $count (OK)" ;;
      3*) echo "  $status: $count (Redirect)" ;;
      4*) echo "  $status: $count (Client Error)" ;;
      5*) echo "  $status: $count (Server Error)" ;;
      *) echo "  $status: $count" ;;
    esac
  done
  echo ""

  # Top error responses
  ERROR_RESPONSES=$(awk '$9 >= 400 {print $9}' "$log_file" 2>/dev/null | wc -l || echo "0")
  if [ "$ERROR_RESPONSES" -gt 0 ]; then
    warning "Found $ERROR_RESPONSES error responses (4xx/5xx)"
    echo ""

    info "Most common error status codes:"
    awk '$9 >= 400 {print $9}' "$log_file" 2>/dev/null | sort | uniq -c | sort -rn | head -5 | while read count status; do
      echo "  $status: $count occurrences"
    done
    echo ""
  fi

  # Top requested paths
  info "Top 10 requested paths:"
  awk '{print $7}' "$log_file" 2>/dev/null | sort | uniq -c | sort -rn | head -10 | while read count path; do
    echo "  $count requests: $path"
  done
  echo ""

  # Top client IPs
  info "Top 10 client IP addresses:"
  awk '{print $1}' "$log_file" 2>/dev/null | sort | uniq -c | sort -rn | head -10 | while read count ip; do
    echo "  $count requests from $ip"
  done
  echo ""
}

# Function: Analyze error logs
analyze_errors() {
  local log_file="$LOG_DIR/error.log"

  if [ ! -f "$log_file" ]; then
    warning "Error log file not found: $log_file"
    return
  fi

  echo "=== Error Log Analysis ==="
  echo ""

  # Total errors
  TOTAL_ERRORS=$(wc -l < "$log_file")
  warning "Total error entries: $TOTAL_ERRORS"
  echo ""

  # Error type distribution
  info "Error type distribution:"
  grep -io "^\[[^]]*ERROR[^]]*\]" "$log_file" 2>/dev/null | sort | uniq -c | sort -rn | while read count type; do
    echo "  $type: $count"
  done
  echo ""

  # Most recent errors
  info "5 most recent errors:"
  tail -5 "$log_file" | while read line; do
    echo "  $line"
  done
  echo ""
}

# Function: Find error spikes
find_error_spikes() {
  echo "=== Error Spike Detection ==="
  echo ""

  info "Checking for error spikes in the last hour..."

  local spike_threshold=10
  local current_hour=$(date +%Y-%m-%d\ %H)

  for log_file in "$LOG_DIR"/*.log; do
    if [ -f "$log_file" ]; then
      log_name=$(basename "$log_file")
      error_count=$(grep -c "$current_hour" "$log_file" 2>/dev/null | grep -c "error\|Error\|ERROR" || echo "0")

      if [ "$error_count" -gt "$spike_threshold" ]; then
        warning "SPIKE: $error_count errors in $log_name in the current hour"
      fi
    fi
  done

  echo ""
}

# Function: Generate hourly error trend
generate_error_trend() {
  echo "=== Hourly Error Trend (Last $HOURS Hours) ==="
  echo ""

  for hour in $(seq $((HOURS - 1)) -1 0); do
    target_time=$((CURRENT_TIME - hour * 3600))
    target_date=$(date -d "@$target_time" +"%Y-%m-%d %H:00")

    error_count=0
    for log_file in "$LOG_DIR"/*.log; do
      if [ -f "$log_file" ]; then
        count=$(grep -c "$target_date" "$log_file" 2>/dev/null | grep -ic "error\|failed\|exception" || echo "0")
        error_count=$((error_count + count))
      fi
    done

    # Create simple bar chart
    bar=$(printf '%*s' "$((error_count / 10))" | tr ' ' '=')
    echo "$target_date: $bar $error_count errors"
  done

  echo ""
}

# Function: Generate report
generate_report() {
  local report_file="$ANALYSIS_REPORT_DIR/log-analysis-$(date +%Y%m%d-%H%M%S).txt"

  {
    echo "=========================================="
    echo "L30 Library Log Analysis Report"
    echo "=========================================="
    echo "Generated: $(date)"
    echo "Analysis period: Last $HOURS hours"
    echo "Time range: $START_DATE to $CURRENT_DATE"
    echo ""
  } > "$report_file"

  case "$LOG_TYPE" in
    backend)
      analyze_backend >> "$report_file"
      ;;
    database)
      analyze_database >> "$report_file"
      ;;
    nginx)
      analyze_nginx >> "$report_file"
      ;;
    error)
      analyze_errors >> "$report_file"
      ;;
    all)
      analyze_backend >> "$report_file"
      echo "" >> "$report_file"
      analyze_database >> "$report_file"
      echo "" >> "$report_file"
      analyze_nginx >> "$report_file"
      echo "" >> "$report_file"
      analyze_errors >> "$report_file"
      echo "" >> "$report_file"
      find_error_spikes >> "$report_file"
      echo "" >> "$report_file"
      generate_error_trend >> "$report_file"
      ;;
  esac

  {
    echo "=========================================="
    echo "Report saved to: $report_file"
  } >> "$report_file"

  success "Report generated: $report_file"
  echo ""

  # Display report
  cat "$report_file"
}

# Main execution
case "$LOG_TYPE" in
  backend)
    info "Analyzing backend logs..."
    analyze_backend
    ;;
  database)
    info "Analyzing database logs..."
    analyze_database
    ;;
  nginx)
    info "Analyzing Nginx logs..."
    analyze_nginx
    ;;
  error)
    info "Analyzing error logs..."
    analyze_errors
    ;;
  all)
    info "Analyzing all logs..."
    analyze_backend
    echo ""
    analyze_database
    echo ""
    analyze_nginx
    echo ""
    analyze_errors
    echo ""
    find_error_spikes
    echo ""
    generate_error_trend
    ;;
  *)
    error "Unknown log type: $LOG_TYPE"
    error "Valid types: all, backend, database, nginx, error"
    exit 1
    ;;
esac

# Generate full report
info "Generating detailed report..."
generate_report

exit 0
