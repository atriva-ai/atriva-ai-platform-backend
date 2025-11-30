"""
Database migration to add vehicle tracking fields to cameras table
"""
from sqlalchemy import text
from app.database import engine

def upgrade():
    """Add vehicle tracking fields to cameras table"""
    with engine.connect() as conn:
        # Add vehicle_tracking_enabled column
        conn.execute(text("""
            ALTER TABLE cameras 
            ADD COLUMN IF NOT EXISTS vehicle_tracking_enabled BOOLEAN DEFAULT FALSE
        """))
        
        # Add vehicle_tracking_config column
        conn.execute(text("""
            ALTER TABLE cameras 
            ADD COLUMN IF NOT EXISTS vehicle_tracking_config JSONB
        """))
        
        conn.commit()
        print("✅ Added vehicle tracking fields to cameras table")

def downgrade():
    """Remove vehicle tracking fields from cameras table"""
    with engine.connect() as conn:
        # Remove vehicle_tracking_config column
        conn.execute(text("""
            ALTER TABLE cameras 
            DROP COLUMN IF EXISTS vehicle_tracking_config
        """))
        
        # Remove vehicle_tracking_enabled column
        conn.execute(text("""
            ALTER TABLE cameras 
            DROP COLUMN IF EXISTS vehicle_tracking_enabled
        """))
        
        conn.commit()
        print("✅ Removed vehicle tracking fields from cameras table")

if __name__ == "__main__":
    print("Running database migration for vehicle tracking...")
    upgrade()
    print("Migration completed successfully!")
