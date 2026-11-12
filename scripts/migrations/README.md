# Migration Scripts

Production-ready scripts for safe Alembic migration deployment.

## Quick Start

```bash
# 1. Preview migration
./migrate.sh --dry-run

# 2. Run migration
./migrate.sh

# 3. Verify success
./verify-migrations.sh
```

## Available Scripts

### `migrate.sh` - Main Migration Script
Safely runs Alembic migrations with comprehensive error handling.

```bash
# Usage
./migrate.sh [options]

# Options
--dry-run          # Preview changes without applying
--target REVISION  # Migrate to specific revision
--skip-verification # Skip post-migration checks
--no-backup        # Skip backup (not recommended)

# Examples
./migrate.sh                    # Migrate to latest
./migrate.sh --dry-run          # Preview
./migrate.sh --target 005       # Migrate to specific version
```

**Features:**
- Automatic database backup
- Dry-run mode for preview
- Comprehensive logging
- Post-migration verification
- Detailed error messages
- Duration tracking

**Exit Codes:**
- 0: Success
- 1: Migration failed
- 2: Verification failed
- 3: Database connection failed
- 4: Backup failed

---

### `rollback.sh` - Rollback Script
Safely rolls back migrations.

```bash
# Usage
./rollback.sh [options]

# Options
--steps N          # Rollback N migrations (default: 1)
--target REVISION  # Rollback to specific revision
--dry-run          # Preview rollback
--force            # Skip confirmation

# Examples
./rollback.sh                   # Rollback last migration
./rollback.sh --steps 3         # Rollback 3 migrations
./rollback.sh --target 003      # Rollback to revision 003
./rollback.sh --force           # Emergency rollback
```

**Features:**
- Emergency backup before rollback
- Confirmation prompts
- Dry-run mode
- Post-rollback verification

**Exit Codes:**
- 0: Success
- 1: Rollback failed
- 2: Verification failed
- 3: Database connection failed

---

### `verify-migrations.sh` - Verification Script
Validates database schema after migrations.

```bash
# Usage
./verify-migrations.sh [options]

# Options
--verbose, -v     # Show detailed output

# Examples
./verify-migrations.sh          # Standard verification
./verify-migrations.sh -v       # Verbose output
```

**Checks:**
- Migration history integrity
- Core tables existence
- Foreign key constraints
- Indexes
- Enum types
- Sequences
- Check constraints

**Exit Codes:**
- 0: All checks passed
- 1: One or more checks failed

---

### `backup-migration.sh` - Backup Script
Creates database backups before migrations.

```bash
# Usage
./backup-migration.sh [backup_label]

# Examples
./backup-migration.sh                      # Auto-generated label
./backup-migration.sh "pre_feature_x"      # Custom label
```

**Features:**
- Compressed backups (gzip)
- Metadata files
- Automatic cleanup (keeps last 10)

**Backup Location:** `/opt/l30/backups/migrations/`

---

### `generate-migrations.sh` - Migration Generator
Auto-generates migration files from model changes.

```bash
# Usage
./generate-migrations.sh --message "description" [options]

# Options
--message MSG      # Migration description (required)
--autogenerate     # Use alembic autogenerate (default)
--empty            # Create empty migration
--review           # Review before saving

# Examples
./generate-migrations.sh --message "add user preferences table"
./generate-migrations.sh --message "update indexes" --review
./generate-migrations.sh --message "custom data migration" --empty
```

**Features:**
- Automatic schema detection
- Sequential revision IDs
- Syntax validation
- Interactive review mode

---

## Directory Structure

```
/opt/l30/
├── scripts/migrations/
│   ├── migrate.sh              # Main migration script
│   ├── rollback.sh             # Rollback script
│   ├── verify-migrations.sh    # Verification script
│   ├── backup-migration.sh     # Backup script
│   ├── generate-migrations.sh  # Migration generator
│   └── README.md              # This file
├── logs/migrations/
│   ├── migration_*.log        # Migration execution logs
│   ├── rollback_*.log         # Rollback logs
│   ├── verification_*.log     # Verification logs
│   └── metrics.json           # Migration metrics
├── backups/migrations/
│   ├── *.sql.gz               # Database backups
│   └── *.sql.gz.meta          # Backup metadata
└── docs/migrations/
    ├── DEPLOYMENT_GUIDE.md    # Complete deployment guide
    ├── TROUBLESHOOTING.md     # Common issues & fixes
    ├── TESTING_STRATEGY.md    # Testing approach
    ├── DEPLOYMENT_CHECKLIST.md # Step-by-step checklist
    └── RISK_MITIGATION.md     # Risk management
```

---

## Environment Variables

Required:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

Optional:
```bash
ENVIRONMENT=production         # Environment name
LOG_LEVEL=INFO                # Logging level
SENTRY_DSN=https://...        # Error tracking
```

---

## Common Workflows

### Development: Generate and Apply Migration
```bash
# 1. Generate migration from model changes
./generate-migrations.sh --message "add email verification"

# 2. Review generated file
cat /opt/l30/backend/alembic/versions/006_*.py

# 3. Apply migration
./migrate.sh --no-backup --skip-verification
```

### Staging: Test Before Production
```bash
# 1. Preview changes
./migrate.sh --dry-run

# 2. Apply with full verification
./migrate.sh

# 3. Verify all checks pass
./verify-migrations.sh --verbose

# 4. Test rollback
./rollback.sh --dry-run
```

### Production: Safe Deployment
```bash
# 1. Create backup
./backup-migration.sh "pre_feature_x_$(date +%Y%m%d)"

# 2. Preview migration
./migrate.sh --dry-run > /tmp/migration-plan.txt
cat /tmp/migration-plan.txt

# 3. Execute migration
./migrate.sh 2>&1 | tee /tmp/production-migration.log

# 4. Verify success
./verify-migrations.sh

# 5. Monitor logs
tail -f /opt/l30/logs/migrations/migration_*.log
```

### Emergency: Rollback Production
```bash
# Quick rollback
./rollback.sh --force

# Verify rollback
./verify-migrations.sh

# Restore from backup if rollback fails
cd /opt/l30/backups/migrations
gunzip -c latest.sql.gz | psql $DATABASE_URL
```

---

## Logging

All scripts log to:
- **Console:** Real-time output with colors
- **Files:** `/opt/l30/logs/migrations/`
- **Format:** `[TIMESTAMP] [LEVEL] message`

View logs:
```bash
# Latest migration log
tail -f /opt/l30/logs/migrations/migration_*.log

# All recent logs
ls -lht /opt/l30/logs/migrations/ | head -10

# Search for errors
grep ERROR /opt/l30/logs/migrations/*.log
```

---

## Monitoring

### Metrics Collected
- Migration duration
- Success/failure rate
- Verification results
- Rollback frequency

Metrics location: `/opt/l30/logs/migrations/metrics.json`

### Integration with Monitoring Systems

```python
# Example: Prometheus metrics
from prometheus_client import Counter, Histogram

migration_counter = Counter('migration_executions_total', 'Total migrations', ['status'])
migration_duration = Histogram('migration_duration_seconds', 'Migration duration')
```

---

## Best Practices

1. **Always test in staging first**
2. **Never skip backups in production**
3. **Use --dry-run before applying**
4. **Monitor logs during migration**
5. **Verify after every migration**
6. **Document complex migrations**
7. **Keep migrations small and focused**
8. **Test both upgrade and downgrade**

---

## Troubleshooting

See [TROUBLESHOOTING.md](/opt/l30/docs/migrations/TROUBLESHOOTING.md) for detailed solutions.

### Quick Fixes

**Migration fails with "relation already exists"**
```bash
cd /opt/l30/backend
alembic stamp head
```

**Can't connect to database**
```bash
# Check connection
psql $DATABASE_URL -c "SELECT 1"

# Verify URL
echo $DATABASE_URL
```

**Out of disk space**
```bash
# Clean old backups
rm /opt/l30/backups/migrations/migration_202*.sql.gz

# Clean old logs
find /opt/l30/logs/migrations -mtime +30 -delete
```

---

## Support

- **Documentation:** `/opt/l30/docs/migrations/`
- **Logs:** `/opt/l30/logs/migrations/`
- **Slack:** #database-team
- **Emergency:** [on-call contact]

---

## Version

**Version:** 1.0.0
**Last Updated:** 2026-02-13
**Maintained By:** Database Team
