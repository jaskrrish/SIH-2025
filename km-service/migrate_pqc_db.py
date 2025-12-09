"""
Database migration: Add PQC key table for QKD+PQC encryption level
Run this to migrate the KM service database
"""
from database import db, init_db
from models import PQCKey
from flask import Flask
import os

# Create Flask app for migration
app = Flask(__name__)

# Initialize database
init_db(app)

def migrate():
    """Run migration to add PQC key table"""
    print("=" * 60)
    print("🔐 KM Service Database Migration: Add PQC Key Table")
    print("=" * 60)
    
    try:
        # Create all tables (will only create missing ones)
        with app.app_context():
            db.create_all()
            print("✅ Successfully created PQC key table")
            print(f"   - Database: {os.getenv('DATABASE_URL', 'sqlite:///instance/km_keys.db')}")
            print(f"   - Table: pqc_keys")
            print("=" * 60)
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("=" * 60)
        raise

if __name__ == '__main__':
    migrate()
