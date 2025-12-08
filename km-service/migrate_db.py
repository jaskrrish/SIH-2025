"""
Database migration script for KM Service
Drops old table and creates new schema with correct column sizes
"""
from database import db, init_db
from models import QKDKey
from flask import Flask
import os

# Create Flask app
app = Flask(__name__)

# Get database URL from environment or use default
database_url = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_tBWbHk32Z1kS@ep-falling-meadow-a1yrdxgp.ap-southeast-1.aws.neon.tech/neondb?sslmode=require')

# Configure app
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

def migrate():
    """Run migration"""
    with app.app_context():
        print("[MIGRATION] Starting database migration...")
        
        try:
            # Drop existing table
            print("[MIGRATION] Dropping old qkd_keys table...")
            db.session.execute(db.text('DROP TABLE IF EXISTS qkd_keys CASCADE'))
            db.session.commit()
            print("[MIGRATION] ✅ Old table dropped")
            
            # Create new table with updated schema
            print("[MIGRATION] Creating new qkd_keys table...")
            db.create_all()
            print("[MIGRATION] ✅ New table created with updated schema")
            
            print("\n[MIGRATION] Schema changes:")
            print("  - key_id: VARCHAR(36) → VARCHAR(50)")
            print("  - pair_key_id: VARCHAR(36) → VARCHAR(50)")
            print("  - created_at: Fixed deprecation warnings (timezone-aware)")
            print("\n[MIGRATION] ✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"[MIGRATION] ❌ Migration failed: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate()
