"""
Database utility functions for handling optional columns across different app deployments
"""
from sqlalchemy import inspect, text
from app.database import engine
from typing import Set

# Cache for column existence checks
_column_cache: dict = {}

def column_exists(table_name: str, column_name: str) -> bool:
    """
    Check if a column exists in a table.
    Uses caching to avoid repeated database queries.
    """
    cache_key = f"{table_name}.{column_name}"
    
    if cache_key not in _column_cache:
        try:
            with engine.connect() as conn:
                # Check if column exists in the table
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = :table_name 
                    AND column_name = :column_name
                """), {"table_name": table_name, "column_name": column_name})
                
                _column_cache[cache_key] = result.fetchone() is not None
        except Exception as e:
            # If we can't check, assume it doesn't exist to be safe
            print(f"⚠️ Warning: Could not check column existence for {cache_key}: {e}")
            _column_cache[cache_key] = False
    
    return _column_cache[cache_key]

def get_camera_optional_columns() -> Set[str]:
    """
    Returns a set of optional column names that may not exist in all deployments.
    These columns are used by some apps but not others.
    """
    return {"vehicle_tracking_enabled", "vehicle_tracking_config"}

def should_defer_vehicle_tracking() -> bool:
    """
    Check if vehicle tracking columns exist. If not, they should be deferred in queries.
    """
    return not column_exists("cameras", "vehicle_tracking_enabled")

