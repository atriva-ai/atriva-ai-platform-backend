"""
Database migration to add person detection enabled field to cameras table
"""
from sqlalchemy import text
from app.database import engine

def upgrade():
    """Add person_detection_enabled field to cameras table"""

    with engine.begin() as conn:
        # Add person_detection_enabled column
        conn.execute(text("""
            ALTER TABLE cameras 
            ADD COLUMN IF NOT EXISTS person_detection_enabled BOOLEAN DEFAULT TRUE
        """))
        
        print("✅ Added person_detection_enabled field to cameras table")

def downgrade():
    """Remove person_detection_enabled field from cameras table"""
    with engine.begin() as conn:
        # Remove person_detection_enabled column
        conn.execute(text("""
            ALTER TABLE cameras 
            DROP COLUMN IF EXISTS person_detection_enabled
        """))
        
        print("✅ Removed person_detection_enabled field from cameras table")

if __name__ == "__main__":
    print("Running database migration for person detection...")
    upgrade()
    print("Migration completed successfully!")

