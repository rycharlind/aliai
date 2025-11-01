# Database Migrations

This directory contains database migration files for managing the ClickHouse schema.

## Migration System

The migration system tracks applied migrations in the `schema_migrations` table and ensures migrations are applied in order, only once.

## Migration File Naming

Migration files must follow this naming pattern:
```
{version:03d}_{descriptive_name}.sql
```

Examples:
- `001_initial_schema.sql`
- `002_add_indexes.sql`
- `003_update_products_table.sql`

## Creating a New Migration

### Using the CLI tool:
```bash
python scripts/migrate.py create --name add_user_preferences --description "Add user preferences table"
```

This will create a new migration file with the next version number and a template.

### Manual creation:
1. Find the highest version number in existing migrations
2. Create a new file: `{next_version:03d}_{name}.sql`
3. Follow the template structure with metadata comments

## Migration File Format

Each migration file should start with metadata comments:

```sql
-- Migration: 002_add_indexes.sql
-- Description: Add performance indexes for common queries
-- Created: 2024-01-15 10:30:00

-- Your migration SQL here
CREATE INDEX IF NOT EXISTS idx_products_title ON products (title) TYPE tokenbf_v1(256, 3, 0);
```

## Running Migrations

### Check migration status:
```bash
python scripts/migrate.py status
```

### Apply pending migrations:
```bash
python scripts/migrate.py migrate
```

### Dry run (see what would be applied):
```bash
python scripts/migrate.py migrate --dry-run
```

### Migrate to specific version:
```bash
python scripts/migrate.py migrate --target 5
```

## ClickHouse-Specific Considerations

### ALTER TABLE Operations
ClickHouse supports `ALTER TABLE` but some operations can be expensive on large tables:
- Adding columns: Generally safe and fast
- Modifying columns: May require data mutation (can be slow)
- Dropping columns: Safe but data is permanently removed

### CREATE IF NOT EXISTS
ClickHouse supports `IF NOT EXISTS` for:
- `CREATE TABLE IF NOT EXISTS`
- `CREATE MATERIALIZED VIEW IF NOT EXISTS`
- `CREATE INDEX IF NOT EXISTS` (v22.8+)

Use these to make migrations idempotent.

### Materialized Views
When modifying tables that have materialized views, you may need to:
1. Drop the materialized view
2. Apply the table change
3. Recreate the materialized view

### Best Practices

1. **Test migrations on a copy of production data** - ClickHouse doesn't support transactional DDL
2. **Keep migrations small and focused** - One logical change per migration
3. **Document breaking changes** - Add comments for schema changes that require application updates
4. **Use IF NOT EXISTS** - Makes migrations safe to re-run
5. **Avoid data migrations in schema files** - Use separate scripts for large data transformations
6. **Document rollback procedures** - ClickHouse doesn't auto-rollback, document manual steps if needed

## Migration Tracking

Applied migrations are tracked in the `schema_migrations` table with:
- `migration_id`: Unique identifier (version_name)
- `version`: Numeric version
- `name`: Migration name
- `description`: Migration description
- `applied_at`: Timestamp when applied
- `checksum`: MD5 checksum of migration content
- `execution_time_ms`: Time taken to apply

## Rollback

ClickHouse doesn't support transactional DDL operations, so automatic rollback is not fully supported. If you need to rollback:

1. Create a new migration that undoes the change
2. Document manual rollback steps in migration comments
3. For data migrations, create a separate rollback script

## Integration

The migration system is integrated with:
- `scripts/init_database.py` - Automatically runs migrations on database initialization
- `scripts/migrate.py` - Standalone migration CLI tool

## Example Migration Workflow

1. Create a new migration:
   ```bash
   python scripts/migrate.py create --name add_product_views --description "Add product_views table"
   ```

2. Edit the generated migration file:
   ```sql
   -- Migration: 002_add_product_views.sql
   -- Description: Add product_views table
   -- Created: 2024-01-15 10:30:00

   CREATE TABLE IF NOT EXISTS product_views (
       product_id String,
       user_id String,
       viewed_at DateTime DEFAULT now()
   ) ENGINE = MergeTree()
   ORDER BY (product_id, viewed_at);
   ```

3. Check status:
   ```bash
   python scripts/migrate.py status
   ```

4. Apply migration:
   ```bash
   python scripts/migrate.py migrate
   ```

