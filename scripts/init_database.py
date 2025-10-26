"""
AliAI - Database Initialization Script
Creates ClickHouse database and tables
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from aliai.database import ClickHouseClient
from aliai.config import get_config


async def init_database():
    """Initialize ClickHouse database and tables"""
    config = get_config()
    
    print("Initializing AliAI database...")
    
    try:
        # Connect to ClickHouse
        db = ClickHouseClient()
        
        # Test connection
        if not db.test_connection():
            print("❌ Failed to connect to ClickHouse")
            return False
        
        print("✅ Connected to ClickHouse")
        
        # Read schema file
        schema_file = project_root / "schema" / "clickhouse_schema.sql"
        
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Split SQL statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        print(f"Executing {len(statements)} SQL statements...")
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            try:
                if statement.upper().startswith('CREATE TABLE'):
                    table_name = statement.split()[2]
                    print(f"  {i}. Creating table: {table_name}")
                elif statement.upper().startswith('CREATE MATERIALIZED VIEW'):
                    view_name = statement.split()[3]
                    print(f"  {i}. Creating materialized view: {view_name}")
                elif statement.upper().startswith('CREATE INDEX'):
                    index_name = statement.split()[2]
                    print(f"  {i}. Creating index: {index_name}")
                else:
                    print(f"  {i}. Executing statement...")
                
                db.client.execute(statement)
                
            except Exception as e:
                print(f"  ❌ Error executing statement {i}: {e}")
                # Continue with other statements
                continue
        
        print("✅ Database initialization completed")
        
        # Verify tables were created
        tables_result = db.client.execute("SHOW TABLES")
        tables = [row[0] for row in tables_result]
        
        print(f"\nCreated tables: {', '.join(tables)}")
        
        # Test data insertion
        print("\nTesting data insertion...")
        
        # Insert sample data into categories
        sample_categories = [
            ('electronics', 'Electronics', '', 1, 'Electronics', {'summer': 0.3, 'winter': 0.2}, 0.0, 0, 0.0),
            ('clothing', 'Clothing', '', 1, 'Clothing', {'summer': 0.8, 'winter': 0.9}, 0.0, 0, 0.0),
            ('home', 'Home & Garden', '', 1, 'Home & Garden', {'spring': 0.7, 'fall': 0.6}, 0.0, 0, 0.0),
            ('beauty', 'Beauty & Health', '', 1, 'Beauty & Health', {'summer': 0.5, 'winter': 0.4}, 0.0, 0, 0.0),
            ('sports', 'Sports & Outdoors', '', 1, 'Sports & Outdoors', {'summer': 0.9, 'winter': 0.3}, 0.0, 0, 0.0)
        ]
        
        insert_query = """
        INSERT INTO categories (
            category_id, category_name, parent_category_id, level, path,
            seasonal_relevance, trend_score, product_count, avg_price, created_at, updated_at
        ) VALUES
        """
        
        for category_data in sample_categories:
            db.client.execute(insert_query, category_data + (None, None))
        
        print("✅ Sample data inserted")
        
        # Get table statistics
        stats_query = "SELECT count() FROM categories"
        result = db.client.execute(stats_query)
        count = result[0][0]
        print(f"Categories table now has {count} records")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


async def main():
    """Main function"""
    success = await init_database()
    
    if success:
        print("\n🎉 Database initialization completed successfully!")
        print("\nNext steps:")
        print("1. Configure your .env file with API keys")
        print("2. Start scraping: python main.py --mode scrape")
        print("3. Run analysis: python main.py --mode analyze")
        print("4. Generate insights: python main.py --mode insights")
    else:
        print("\n❌ Database initialization failed!")
        print("Please check your ClickHouse connection and try again.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
