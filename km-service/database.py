"""
Database configuration for KM service
Supports both SQLite (dev) and PostgreSQL (production)
"""
import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()

def init_db(app):
    """Initialize database with Flask app"""
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'sqlite:///km_keys.db')
    
    # SQLAlchemy 1.4+ requires 'postgresql://' instead of 'postgres://'
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        print(f"✅ Database initialized: {database_url}")
