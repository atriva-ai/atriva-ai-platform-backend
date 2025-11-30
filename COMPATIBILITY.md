# Backend Compatibility Guide

## Overview

The dashboard backend is shared across multiple applications. Some features (like vehicle tracking) are used by some apps but not others. This document explains how the codebase handles optional database columns to maintain compatibility.

## Vehicle Tracking Fields

The `cameras` table includes optional vehicle tracking fields:
- `vehicle_tracking_enabled` (BOOLEAN, default: FALSE)
- `vehicle_tracking_config` (JSONB, nullable)

These fields are:
- **Defined in the model** - So other apps that need them can use them
- **Optional in the database** - Apps that don't need them don't have to add these columns
- **Gracefully handled** - The code automatically detects missing columns and handles them

## How It Works

### 1. Column Detection (`app/db/utils.py`)

The `column_exists()` function checks if a column exists in the database:
- Uses caching to avoid repeated queries
- Returns `True` if column exists, `False` otherwise

The `should_defer_vehicle_tracking()` function determines if vehicle tracking columns should be excluded from queries.

### 2. Query Handling (`app/db/crud/camera.py`)

All camera queries use SQLAlchemy's `defer()` to exclude vehicle tracking columns when they don't exist:
- `get_cameras()` - Defers vehicle tracking columns
- `get_camera()` - Defers vehicle tracking columns
- `create_camera()` - Excludes vehicle tracking fields from data
- `update_camera()` - Excludes vehicle tracking fields from updates

### 3. Model Handling (`app/db/models/camera.py`)

The `Camera` model includes a `__getattr__()` method that:
- Returns default values for vehicle tracking attributes when columns don't exist
- Prevents AttributeError when accessing these fields
- Only activates when `should_defer_vehicle_tracking()` returns `True`

### 4. Schema Handling (`app/db/schemas/camera.py`)

Pydantic schemas handle missing attributes gracefully:
- `CameraInDB`, `CameraOut`, and `CameraRead` override `model_validate()` to set defaults
- Ensures serialization works even when columns are missing

### 5. Migration (`app/db/migrations/add_vehicle_tracking.py`)

The migration script:
- Adds vehicle tracking columns if they don't exist
- Uses `IF NOT EXISTS` to be idempotent
- Can be run safely multiple times

## Usage

### For Apps That Need Vehicle Tracking

1. Run the migration to add columns:
   ```python
   from app.db.migrations.add_vehicle_tracking import upgrade
   upgrade()
   ```

2. The columns will be automatically included in queries and updates.

### For Apps That Don't Need Vehicle Tracking

1. **Do nothing!** The code automatically handles missing columns.

2. The system will:
   - Skip these columns in queries (using `defer()`)
   - Return default values when accessed
   - Exclude them from create/update operations

## Adding New Optional Features

To add new optional features that some apps need but others don't:

1. **Add to model** - Define the column in the model with appropriate defaults
2. **Add to utils** - Add column name to `get_camera_optional_columns()` and create a check function
3. **Update CRUD** - Use `defer()` in queries and exclude from create/update when columns don't exist
4. **Update model** - Add to `__getattr__()` to return defaults
5. **Update schemas** - Handle in `model_validate()` if needed
6. **Create migration** - Optional migration script to add columns

## Testing

To test compatibility:

1. **With columns**: Run migration, verify all features work
2. **Without columns**: Don't run migration, verify app still works with defaults

## Notes

- The migration in `main.py` is optional - it tries to add columns but failures are handled gracefully
- Column existence is cached to avoid performance issues
- All vehicle tracking fields have sensible defaults (False for boolean, None for JSON)

