"""
AliAI - Database Initialization Script
Convenience script for initial database setup (first-time initialization)
For ongoing migrations, use: python scripts/migrate.py migrate
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from aliai.database import ClickHouseClient
from aliai.migrations import MigrationManager


def init_database():
    """Initialize ClickHouse database using migration system"""
    print("Initializing AliAI database...")
    
    try:
        # Test connection first
        db = ClickHouseClient()
        
        if not db.test_connection():
            print("❌ Failed to connect to ClickHouse")
            return False
        
        print("✅ Connected to ClickHouse")
        db.close()
        
        # Run migrations
        print("\nRunning database migrations...")
        manager = MigrationManager()
        
        # Check current status
        status = manager.get_status()
        print(f"  Found {status['total_files']} migration file(s)")
        print(f"  {status['applied']} already applied, {status['pending']} pending")
        
        # Apply migrations
        if status['pending'] > 0:
            print("\nApplying pending migrations...")
            success = manager.migrate()
            
            if not success:
                print("❌ Migration failed")
                manager.close()
                return False
            
            print("✅ All migrations applied successfully")
        else:
            print("✅ Database is up to date")
        
        manager.close()
        
        # Verify tables were created
        print("\nVerifying database schema...")
        db = ClickHouseClient()
        
        tables_result = db.client.execute("SHOW TABLES")
        tables = [row[0] for row in tables_result]
        
        # Filter out migrations table from output
        user_tables = [t for t in tables if t != 'schema_migrations']
        
        print(f"✅ Database tables: {', '.join(user_tables)}")
        
        # Test data insertion (optional - for development/testing)
        print("\nTesting data insertion...")
        
        # Insert sample data into categories
        # Format: (category_id, category_name, parent_category_id, level, path,
        #          seasonal_relevance, trend_score, product_count, avg_price)
        sample_categories = [
            ('electronics', 'Electronics', '', 1, 'Electronics', {'summer': 0.3, 'winter': 0.2}, 0.0, 0, 0.0),
            ('clothing', 'Clothing', '', 1, 'Clothing', {'summer': 0.8, 'winter': 0.9}, 0.0, 0, 0.0),
            ('home', 'Home & Garden', '', 1, 'Home & Garden', {'spring': 0.7, 'fall': 0.6}, 0.0, 0, 0.0),
            ('beauty', 'Beauty & Health', '', 1, 'Beauty & Health', {'summer': 0.5, 'winter': 0.4}, 0.0, 0, 0.0),
            ('sports', 'Sports & Outdoors', '', 1, 'Sports & Outdoors', {'summer': 0.9, 'winter': 0.3}, 0.0, 0, 0.0)
        ]
        
        # Use ClickHouse native client execute method for proper data handling
        # This is more reliable for Map types and complex data structures
        
        columns = [
            'category_id', 'category_name', 'parent_category_id', 'level', 'path',
            'seasonal_relevance', 'trend_score', 'product_count', 'avg_price'
        ]
        
        data = []
        for cat_data in sample_categories:
            row = [
                cat_data[0],  # category_id
                cat_data[1],  # category_name
                cat_data[2],  # parent_category_id
                cat_data[3],  # level
                cat_data[4],  # path
                cat_data[5],  # seasonal_relevance (Map)
                cat_data[6],  # trend_score
                cat_data[7],  # product_count
                cat_data[8]   # avg_price
            ]
            data.append(row)
        
        db.client.execute(
            'INSERT INTO categories ({}) VALUES'.format(','.join(columns)),
            data
        )
        
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
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    success = init_database()
    
    if success:
        print("\n🎉 Database initialization completed successfully!")
        print("\nNext steps:")
        print("1. Configure your .env file with API keys")
        print("2. Start scraping: python main.py --mode scrape")
        print("3. Run analysis: python main.py --mode analyze")
        print("4. Generate insights: python main.py --mode insights")
        print("\nFor future migrations, use: python scripts/migrate.py migrate")
    else:
        print("\n❌ Database initialization failed!")
        print("Please check your ClickHouse connection and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
