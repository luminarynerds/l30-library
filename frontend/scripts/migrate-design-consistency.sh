#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

################################################################################
# Design Consistency Migration Script
# Little Schitt Creek Library Frontend
#
# This script helps migrate components to use semantic border radius utilities
# and fix color token issues.
#
# IMPORTANT: This script performs find-and-replace operations.
# - Always run in a clean git branch
# - Review all changes before committing
# - Test thoroughly after running
#
# Usage:
#   ./scripts/migrate-design-consistency.sh [--dry-run] [--step STEP_NUMBER]
#
# Options:
#   --dry-run         Show what would be changed without making changes
#   --step NUMBER     Run only a specific step (1-5)
#   --help            Show this help message
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Options
DRY_RUN=false
STEP=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --step)
      STEP="$2"
      shift 2
      ;;
    --help)
      head -n 20 "$0" | tail -n +3
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Helper functions
log_info() {
  echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
  echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
  echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
check_prerequisites() {
  log_info "Checking prerequisites..."

  if ! command -v git &> /dev/null; then
    log_error "git is required but not installed"
    exit 1
  fi

  if ! command -v sed &> /dev/null; then
    log_error "sed is required but not installed"
    exit 1
  fi

  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Not in a git repository"
    exit 1
  fi

  if [[ -n $(git status --porcelain) ]] && [[ "$DRY_RUN" == "false" ]]; then
    log_warning "Working directory is not clean. Uncommitted changes detected."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi

  log_success "Prerequisites check passed"
}

# Create backup
create_backup() {
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry run mode - skipping backup"
    return
  fi

  local BACKUP_BRANCH="backup-before-design-migration-$(date +%Y%m%d-%H%M%S)"
  log_info "Creating backup branch: $BACKUP_BRANCH"
  git branch "$BACKUP_BRANCH"
  log_success "Backup created: $BACKUP_BRANCH"
}

# Safe sed that works on both macOS and Linux
safe_sed() {
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "Would run: sed $@"
    return
  fi

  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "$@"
  else
    sed -i "$@"
  fi
}

# Find and replace in files
find_and_replace() {
  local pattern=$1
  local replacement=$2
  local file_pattern=$3
  local description=$4

  log_info "$description"

  if [[ "$DRY_RUN" == "true" ]]; then
    local count=$(find "$PROJECT_ROOT/src" -type f -name "$file_pattern" -exec grep -l "$pattern" {} \; | wc -l)
    log_warning "DRY RUN: Would update $count files"
    return
  fi

  local files=($(find "$PROJECT_ROOT/src" -type f -name "$file_pattern" -exec grep -l "$pattern" {} \;))
  local count=${#files[@]}

  if [[ $count -eq 0 ]]; then
    log_info "No files to update"
    return
  fi

  for file in "${files[@]}"; do
    safe_sed "s/$pattern/$replacement/g" "$file"
  done

  log_success "Updated $count files"
}

################################################################################
# STEP 1: Border Radius - Buttons
################################################################################
step1_migrate_buttons() {
  log_info "========== STEP 1: Migrating Button Border Radius =========="

  # Primary buttons (previously rounded-2xl)
  find_and_replace \
    'className="\([^"]*\)rounded-2xl\([^"]*\)"[^>]*>\([^<]*\)\(Join\|Submit\|Save\|Send\|Register\|Continue\|Confirm\)' \
    'className="\1rounded-button-primary\2">\3\4' \
    "*.tsx" \
    "Migrating primary button border radius..."

  # Secondary/Cancel buttons (previously rounded-lg or rounded-xl)
  find_and_replace \
    'className="\([^"]*\)rounded-\(lg\|xl\)\([^"]*\)"[^>]*>\([^<]*\)\(Cancel\|Close\|Back\)' \
    'className="\1rounded-button-secondary\3">\4\5' \
    "*.tsx" \
    "Migrating secondary button border radius..."

  log_success "Step 1 complete"
}

################################################################################
# STEP 2: Border Radius - Cards and Containers
################################################################################
step2_migrate_cards() {
  log_info "========== STEP 2: Migrating Card Border Radius =========="

  # Standard cards (rounded-lg or rounded-2xl)
  find_and_replace \
    'className="\([^"]*\)bg-white\([^"]*\)border\([^"]*\)rounded-\(lg\|2xl\)' \
    'className="\1bg-white\2border\3rounded-card' \
    "*.tsx" \
    "Migrating card border radius..."

  # Dark mode cards
  find_and_replace \
    'className="\([^"]*\)bg-white dark:bg-\([^"]*\)border\([^"]*\)rounded-\(lg\|2xl\)' \
    'className="\1bg-white dark:bg-\2border\3rounded-card' \
    "*.tsx" \
    "Migrating dark mode card border radius..."

  log_success "Step 2 complete"
}

################################################################################
# STEP 3: Border Radius - Inputs and Form Fields
################################################################################
step3_migrate_inputs() {
  log_info "========== STEP 3: Migrating Input Border Radius =========="

  # Text inputs
  find_and_replace \
    '<input\([^>]*\)className="\([^"]*\)rounded-\(lg\|xl\)' \
    '<input\1className="\2rounded-input' \
    "*.tsx" \
    "Migrating input border radius..."

  # Textareas
  find_and_replace \
    '<textarea\([^>]*\)className="\([^"]*\)rounded-\(lg\|xl\)' \
    '<textarea\1className="\2rounded-input' \
    "*.tsx" \
    "Migrating textarea border radius..."

  # Select elements
  find_and_replace \
    '<select\([^>]*\)className="\([^"]*\)rounded-\(lg\|xl\)' \
    '<select\1className="\2rounded-input' \
    "*.tsx" \
    "Migrating select border radius..."

  log_success "Step 3 complete"
}

################################################################################
# STEP 4: Border Radius - Modals and Dialogs
################################################################################
step4_migrate_modals() {
  log_info "========== STEP 4: Migrating Modal Border Radius =========="

  # Modals with role="dialog"
  find_and_replace \
    'role="dialog"\([^>]*\)className="\([^"]*\)rounded-\(2xl\|3xl\)' \
    'role="dialog"\1className="\2rounded-modal' \
    "*.tsx" \
    "Migrating modal border radius..."

  # Modals with aria-modal
  find_and_replace \
    'aria-modal="true"\([^>]*\)className="\([^"]*\)rounded-\(2xl\|3xl\)' \
    'aria-modal="true"\1className="\2rounded-modal' \
    "*.tsx" \
    "Migrating modal border radius (aria-modal)..."

  log_success "Step 4 complete"
}

################################################################################
# STEP 5: Color Tokens - Amber to LSC Orange
################################################################################
step5_migrate_colors() {
  log_info "========== STEP 5: Migrating Color Tokens =========="

  log_warning "This step requires manual review!"
  log_warning "Not all amber usage should be changed to lsc-orange."
  log_warning "Keep amber for: warnings, alerts, system messages"

  # List files using amber (for manual review)
  log_info "Files using amber colors:"
  find "$PROJECT_ROOT/src" -type f -name "*.tsx" -exec grep -l "amber-" {} \; | head -20

  log_warning "Please review these files manually and change non-alert amber usage to lsc-orange"

  log_success "Step 5 complete (manual review required)"
}

################################################################################
# STEP 6: Generate Report
################################################################################
step6_generate_report() {
  log_info "========== STEP 6: Generating Migration Report =========="

  local REPORT_FILE="$PROJECT_ROOT/MIGRATION_REPORT_$(date +%Y%m%d-%H%M%S).txt"

  {
    echo "Design Consistency Migration Report"
    echo "Generated: $(date)"
    echo ""
    echo "Files modified by migration:"
    git status --short
    echo ""
    echo "Summary of changes:"
    git diff --stat
  } > "$REPORT_FILE"

  log_success "Report generated: $REPORT_FILE"
}

################################################################################
# Main execution
################################################################################
main() {
  echo ""
  log_info "Design Consistency Migration Script"
  log_info "===================================="
  echo ""

  if [[ "$DRY_RUN" == "true" ]]; then
    log_warning "DRY RUN MODE - No changes will be made"
    echo ""
  fi

  check_prerequisites

  if [[ "$DRY_RUN" == "false" ]]; then
    create_backup
  fi

  echo ""

  # Run specific step or all steps
  if [[ -n "$STEP" ]]; then
    case "$STEP" in
      1) step1_migrate_buttons ;;
      2) step2_migrate_cards ;;
      3) step3_migrate_inputs ;;
      4) step4_migrate_modals ;;
      5) step5_migrate_colors ;;
      6) step6_generate_report ;;
      *)
        log_error "Invalid step number: $STEP"
        exit 1
        ;;
    esac
  else
    step1_migrate_buttons
    echo ""
    step2_migrate_cards
    echo ""
    step3_migrate_inputs
    echo ""
    step4_migrate_modals
    echo ""
    step5_migrate_colors
    echo ""
    step6_generate_report
  fi

  echo ""
  log_success "Migration complete!"
  echo ""

  if [[ "$DRY_RUN" == "false" ]]; then
    log_warning "IMPORTANT: Review all changes before committing!"
    log_info "Run: git diff"
    log_info "Then: git add -p (to review and stage changes)"
  fi
}

# Run main function
main
