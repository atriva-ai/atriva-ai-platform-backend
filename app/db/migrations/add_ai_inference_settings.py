"""
Database migration to add AI inference settings to settings table
"""
from sqlalchemy import text
from app.database import engine

def upgrade():
    """Add AI inference settings fields to settings table"""

    with engine.begin() as conn:
        # Add ai_inference_fps column
        conn.execute(text("""
            ALTER TABLE settings 
            ADD COLUMN IF NOT EXISTS ai_inference_fps FLOAT DEFAULT 5.0
        """))
        
        # Add person_detection_enabled_by_default column
        conn.execute(text("""
            ALTER TABLE settings 
            ADD COLUMN IF NOT EXISTS person_detection_enabled_by_default BOOLEAN DEFAULT TRUE
        """))
        
        print("✅ Added AI inference settings fields to settings table")

def downgrade():
    """Remove AI inference settings fields from settings table"""
    with engine.begin() as conn:
        # Remove ai_inference_fps column
        conn.execute(text("""
            ALTER TABLE settings 
            DROP COLUMN IF EXISTS ai_inference_fps
        """))
        
        # Remove person_detection_enabled_by_default column
        conn.execute(text("""
            ALTER TABLE settings 
            DROP COLUMN IF EXISTS person_detection_enabled_by_default
        """))
        
        print("✅ Removed AI inference settings fields from settings table")

if __name__ == "__main__":
    print("Running database migration for AI inference settings...")
    upgrade()
    print("Migration completed successfully!")

