-- SPDX-FileCopyrightText: 2026 Luminary Nerds
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- PostgreSQL initialization script for L30 Library
-- This script runs automatically on first database initialization
-- Location: Mounted to /docker-entrypoint-initdb.d/init-extensions.sql

-- Enable pg_stat_statements for query performance analysis
-- Requires shared_preload_libraries='pg_stat_statements' in postgres config
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Enable pgvector for similarity search (already in base image, but ensure it's created)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create a function to check table bloat (useful for maintenance queries)
CREATE OR REPLACE FUNCTION get_table_bloat_estimate()
RETURNS TABLE (
    schemaname name,
    tablename name,
    real_size bigint,
    extra_size bigint,
    extra_pct numeric,
    bloat_size bigint,
    bloat_pct numeric,
    is_na boolean
) AS $$
SELECT
    schemaname,
    tblname AS tablename,
    bs*tblpages AS real_size,
    (tblpages-est_tblpages)*bs AS extra_size,
    CASE WHEN tblpages > 0 AND tblpages - est_tblpages > 0
        THEN 100 * (tblpages - est_tblpages)/tblpages::numeric
        ELSE 0
    END AS extra_pct,
    CASE WHEN (tblpages-est_tblpages)*bs > 0
        THEN (tblpages-est_tblpages)*bs
        ELSE 0
    END AS bloat_size,
    CASE WHEN tblpages > 0 AND tblpages - est_tblpages > 0
        THEN 100 * (tblpages - est_tblpages)/tblpages::numeric
        ELSE 0
    END AS bloat_pct,
    is_na
FROM (
    SELECT
        ceil(reltuples/((bs-page_hdr)/tpl_size)) + ceil(toasttuples/4) AS est_tblpages,
        tblpages,
        bs,
        tblname,
        schemaname,
        is_na
    FROM (
        SELECT
            (4 + tpl_hdr_size + tpl_data_size + (2*ma)
                - CASE WHEN tpl_hdr_size%ma = 0 THEN ma ELSE tpl_hdr_size%ma END
                - CASE WHEN ceil(tpl_data_size)::int%ma = 0 THEN ma ELSE ceil(tpl_data_size)::int%ma END
            ) AS tpl_size,
            bs - page_hdr AS size_per_block,
            (heappages + toastpages) AS tblpages,
            heappages,
            toastpages,
            reltuples,
            toasttuples,
            bs,
            page_hdr,
            schemaname,
            tblname,
            is_na
        FROM (
            SELECT
                n.nspname AS schemaname,
                c.relname AS tblname,
                c.reltuples AS reltuples,
                c.relpages AS heappages,
                COALESCE(toast.relpages, 0) AS toastpages,
                COALESCE(toast.reltuples, 0) AS toasttuples,
                current_setting('block_size')::numeric AS bs,
                CASE WHEN version()~'mingw32' OR version()~'64-bit|x86_64|ppc64|ia64|amd64' THEN 8 ELSE 4 END AS ma,
                24 AS page_hdr,
                23 + CASE WHEN MAX(COALESCE(s.null_frac,0)) > 0 THEN (7 + COUNT(s.attname)) / 8 ELSE 0::int END
                    + CASE WHEN bool_or(att.attname = 'oid' AND att.attnum < 0) THEN 4 ELSE 0 END AS tpl_hdr_size,
                SUM((1-COALESCE(s.null_frac, 0)) * COALESCE(s.avg_width, 0)) AS tpl_data_size,
                bool_or(att.atttypid = 'pg_catalog.name'::regtype)
                    OR SUM(CASE WHEN att.attnum > 0 THEN 1 ELSE 0 END) <> COUNT(s.attname) AS is_na
            FROM pg_attribute AS att
                JOIN pg_class AS c ON att.attrelid = c.oid
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                LEFT JOIN pg_stats AS s ON s.schemaname=n.nspname
                    AND s.tablename = c.relname AND s.inherited=false AND s.attname=att.attname
                LEFT JOIN pg_class AS toast ON c.reltoastrelid = toast.oid
            WHERE NOT att.attisdropped
                AND c.relkind in ('r', 'm')
                AND n.nspname NOT IN ('pg_catalog', 'information_schema')
            GROUP BY 1,2,3,4,5,6,7,8,9
        ) AS s
    ) AS s2
) AS s3
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
$$ LANGUAGE sql VOLATILE;

-- Create a view for easy dead tuple monitoring
CREATE OR REPLACE VIEW v_table_maintenance_status AS
SELECT
    schemaname,
    relname AS tablename,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    CASE WHEN n_live_tup > 0
        THEN ROUND(100.0 * n_dead_tup / n_live_tup, 2)
        ELSE 0
    END AS dead_tuple_pct,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    vacuum_count,
    autovacuum_count,
    analyze_count,
    autoanalyze_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Grant permissions on monitoring views to the application user
-- (The actual user will be created by the application)
COMMENT ON VIEW v_table_maintenance_status IS 'Provides an overview of table maintenance status including dead tuples and vacuum history';
COMMENT ON FUNCTION get_table_bloat_estimate() IS 'Estimates table bloat based on tuple statistics';
