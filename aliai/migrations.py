"""
AliAI - Migration Management System
Handles database schema migrations for ClickHouse
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger
from clickhouse_driver import Client

from aliai.config import get_config


class MigrationManager:
    """Manages database schema migrations for ClickHouse"""
    
    def __init__(self):
        self.config = get_config()
        self.client = None
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        self._connect()
        self._ensure_migrations_table()
    
    def _connect(self):
        """Establish connection to ClickHouse"""
        try:
            self.client = Client(
                host=self.config.database.host,
                port=self.config.database.port,
                user=self.config.database.user,
                password=self.config.database.password,
                database=self.config.database.database
            )
            logger.info("Connected to ClickHouse for migrations")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise
    
    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id String,
            version UInt32,
            name String,
            description String,
            applied_at DateTime DEFAULT now(),
            checksum String,
            execution_time_ms UInt32
        ) ENGINE = MergeTree()
        ORDER BY (version, applied_at)
        SETTINGS index_granularity = 8192
        """
        
        try:
            self.client.execute(create_table_sql)
            logger.debug("Migrations table ready")
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            raise
    
    def _get_applied_migrations(self) -> List[Dict]:
        """Get list of applied migrations"""
        try:
            query = "SELECT migration_id, version, name, checksum FROM schema_migrations ORDER BY version"
            result = self.client.execute(query)
            
            migrations = []
            for row in result:
                migrations.append({
                    'migration_id': row[0],
                    'version': row[1],
                    'name': row[2],
                    'checksum': row[3]
                })
            return migrations
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def _get_migration_files(self) -> List[Tuple[int, str, Path]]:
        """Get all migration files sorted by version number"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []
        
        migrations = []
        pattern = re.compile(r'^(\d+)_(.+)\.sql$')
        
        for file_path in sorted(self.migrations_dir.glob('*.sql')):
            match = pattern.match(file_path.name)
            if match:
                version = int(match.group(1))
                name = match.group(2)
                migrations.append((version, name, file_path))
            else:
                logger.warning(f"Migration file doesn't match naming pattern: {file_path.name}")
        
        return sorted(migrations, key=lambda x: x[0])
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate simple checksum for migration content"""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _parse_migration_metadata(self, content: str) -> Dict[str, str]:
        """Parse migration metadata from SQL comments"""
        metadata = {
            'description': '',
            'created': ''
        }
        
        # Look for metadata in comments
        desc_match = re.search(r'--\s*Description:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if desc_match:
            metadata['description'] = desc_match.group(1).strip()
        
        created_match = re.search(r'--\s*Created:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if created_match:
            metadata['created'] = created_match.group(1).strip()
        
        return metadata
    
    def _execute_migration(self, version: int, name: str, file_path: Path) -> bool:
        """Execute a single migration file"""
        try:
            logger.info(f"Executing migration: {version:03d}_{name}")
            
            # Read migration file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checksum = self._calculate_checksum(content)
            metadata = self._parse_migration_metadata(content)
            
            # Check if already applied with same checksum
            applied = self._get_applied_migrations()
            for migration in applied:
                if migration['version'] == version and migration['checksum'] == checksum:
                    logger.info(f"Migration {version:03d}_{name} already applied (checksum matches)")
                    return True
            
            # Split SQL statements (handle multiple statements)
            # Simple approach: split by semicolons, handling comments
            # Note: For complex SQL with semicolons in strings, a proper SQL parser would be better
            statements = []
            current_statement = []
            
            for line in content.split('\n'):
                # Remove comments (simple -- comment handling)
                if '--' in line:
                    line = line.split('--')[0]
                
                line = line.strip()
                if not line:
                    continue
                
                # Check if line ends with semicolon
                if line.rstrip().endswith(';'):
                    # Add this line to current statement and finalize
                    line = line.rstrip().rstrip(';')  # Remove trailing semicolon
                    if line:  # Only add if there's content after removing semicolon
                        current_statement.append(line)
                    if current_statement:
                        statements.append(' '.join(current_statement))
                        current_statement = []
                else:
                    current_statement.append(line)
            
            # Add any remaining statement (if file doesn't end with semicolon)
            if current_statement:
                statements.append(' '.join(current_statement))
            
            # Filter out empty statements
            statements = [s.strip() for s in statements if s.strip()]
            
            start_time = datetime.now()
            
            # Execute each statement
            for i, statement in enumerate(statements, 1):
                statement = statement.strip()
                if not statement:
                    continue
                
                try:
                    # Ensure statement ends with semicolon for ClickHouse
                    if not statement.rstrip().endswith(';'):
                        statement = statement.rstrip() + ';'
                    
                    logger.debug(f"  Executing statement {i}/{len(statements)}")
                    self.client.execute(statement)
                except Exception as e:
                    error_msg = str(e).lower()
                    # Handle idempotent operations - some statements may fail if they already exist
                    # This is safe for CREATE IF NOT EXISTS, but ClickHouse may still throw errors
                    is_safe_error = any(phrase in error_msg for phrase in [
                        'already exists',
                        'duplicate',
                        'code: 57',  # ClickHouse error code for table already exists
                        'code: 60',  # ClickHouse error code for unknown table (for IF NOT EXISTS variants)
                    ])
                    
                    if is_safe_error:
                        logger.debug(f"  Statement {i} skipped (already exists): {error_msg}")
                    else:
                        logger.error(f"  Error in statement {i}: {e}")
                        raise
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Record migration
            migration_id = f"{version:03d}_{name}"
            insert_query = """
            INSERT INTO schema_migrations (
                migration_id, version, name, description, checksum, execution_time_ms
            ) VALUES (%(migration_id)s, %(version)s, %(name)s, %(description)s, %(checksum)s, %(time)s)
            """
            
            self.client.execute(insert_query, {
                'migration_id': migration_id,
                'version': version,
                'name': name,
                'description': metadata['description'] or f"Migration {version}",
                'checksum': checksum,
                'time': int(execution_time)
            })
            
            logger.info(f"✅ Migration {version:03d}_{name} applied successfully ({execution_time:.0f}ms)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply migration {version:03d}_{name}: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get migration status"""
        applied = self._get_applied_migrations()
        files = self._get_migration_files()
        
        applied_versions = {m['version'] for m in applied}
        
        status = {
            'total_files': len(files),
            'applied': len(applied),
            'pending': len([f for v, n, f in files if v not in applied_versions]),
            'migrations': []
        }
        
        for version, name, file_path in files:
            migration_info = {
                'version': version,
                'name': name,
                'file': file_path.name,
                'applied': version in applied_versions
            }
            
            # Find applied migration info if exists
            applied_migration = next(
                (m for m in applied if m['version'] == version),
                None
            )
            if applied_migration:
                migration_info['applied_at'] = applied_migration.get('migration_id')
                migration_info['checksum'] = applied_migration.get('checksum')
            
            status['migrations'].append(migration_info)
        
        return status
    
    def migrate(self, target_version: Optional[int] = None, dry_run: bool = False) -> bool:
        """
        Apply pending migrations
        
        Args:
            target_version: If specified, only migrate up to this version
            dry_run: If True, only show what would be migrated without applying
        """
        applied = self._get_applied_migrations()
        files = self._get_migration_files()
        
        if not files:
            logger.warning("No migration files found")
            return False
        
        applied_versions = {m['version'] for m in applied}
        
        # Filter pending migrations
        pending = [(v, n, f) for v, n, f in files 
                  if v not in applied_versions and (target_version is None or v <= target_version)]
        
        if not pending:
            logger.info("No pending migrations")
            return True
        
        logger.info(f"Found {len(pending)} pending migration(s)")
        
        if dry_run:
            logger.info("DRY RUN - Would apply the following migrations:")
            for version, name, _ in pending:
                logger.info(f"  - {version:03d}_{name}")
            return True
        
        # Apply migrations in order
        success = True
        for version, name, file_path in pending:
            if not self._execute_migration(version, name, file_path):
                logger.error(f"Migration {version:03d}_{name} failed. Stopping.")
                success = False
                break
        
        return success
    
    def rollback(self, target_version: int) -> bool:
        """
        Rollback migrations down to target version
        
        Note: ClickHouse doesn't support transactional DDL, so rollback
        must be manually defined in migration files or handled carefully.
        This is a placeholder for future implementation.
        """
        logger.warning("Rollback is not fully supported for ClickHouse migrations")
        logger.warning("ClickHouse doesn't support transactional DDL operations")
        logger.warning("Manual rollback procedures should be documented in migration files")
        return False
    
    def create_migration(self, name: str, description: str = "") -> Path:
        """
        Create a new migration file template
        
        Args:
            name: Migration name (will be sanitized)
            description: Optional description
        
        Returns:
            Path to created migration file
        """
        # Sanitize name
        name = re.sub(r'[^a-z0-9_]', '_', name.lower())
        name = re.sub(r'_+', '_', name)
        
        # Get next version number
        files = self._get_migration_files()
        if files:
            next_version = max(v for v, _, _ in files) + 1
        else:
            next_version = 1
        
        filename = f"{next_version:03d}_{name}.sql"
        file_path = self.migrations_dir / filename
        
        template = f"""-- Migration: {filename}
-- Description: {description or "Add description here"}
-- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-- Write your migration SQL here
-- Example: ALTER TABLE products ADD COLUMN new_field String DEFAULT '';

"""
        
        file_path.write_text(template)
        logger.info(f"Created migration file: {file_path}")
        
        return file_path
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.disconnect()
        logger.info("Migration manager connection closed")


def main():
    """CLI entry point for migration management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AliAI Migration Manager')
    parser.add_argument('command', choices=['status', 'migrate', 'create', 'rollback'],
                       help='Migration command to execute')
    parser.add_argument('--target', type=int, help='Target version for migrate/rollback')
    parser.add_argument('--name', type=str, help='Name for new migration (for create command)')
    parser.add_argument('--description', type=str, help='Description for new migration')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (don\'t apply migrations)')
    
    args = parser.parse_args()
    
    manager = MigrationManager()
    
    try:
        if args.command == 'status':
            status = manager.get_status()
            print(f"\nMigration Status:")
            print(f"  Total files: {status['total_files']}")
            print(f"  Applied: {status['applied']}")
            print(f"  Pending: {status['pending']}")
            print(f"\nMigrations:")
            for mig in status['migrations']:
                status_icon = "✅" if mig['applied'] else "⏳"
                print(f"  {status_icon} {mig['version']:03d}_{mig['name']} - {mig['file']}")
                if mig['applied']:
                    print(f"      Checksum: {mig.get('checksum', 'N/A')}")
        
        elif args.command == 'migrate':
            success = manager.migrate(target_version=args.target, dry_run=args.dry_run)
            sys.exit(0 if success else 1)
        
        elif args.command == 'create':
            if not args.name:
                print("Error: --name is required for create command")
                sys.exit(1)
            file_path = manager.create_migration(args.name, args.description or "")
            print(f"Created migration: {file_path}")
        
        elif args.command == 'rollback':
            if not args.target:
                print("Error: --target is required for rollback command")
                sys.exit(1)
            manager.rollback(args.target)
    
    finally:
        manager.close()


if __name__ == "__main__":
    main()

