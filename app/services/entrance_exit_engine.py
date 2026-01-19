"""
Entrance/Exit Analytics Engine

Processes person centroid events to detect line crossings and emit IN/OUT events.
"""
from typing import Dict, Optional, Any
from datetime import datetime
import time
from app.geometry_utils import detect_line_crossing, should_count_crossing, get_point_side_of_line
from app.db.crud.entry_exit_event import create_entry_exit_event
from sqlalchemy.orm import Session

# Track last position per track_id: {track_id: {'x': float, 'y': float, 'timestamp': float}}
track_positions: Dict[int, Dict[str, Any]] = {}


def process_person_centroid(
    db: Session,
    camera_id: int,
    track_id: int,
    centroid_x: float,
    centroid_y: float,
    line_config: Dict[str, float],
    direction_filter: str = "both",
    timestamp: Optional[float] = None,
    entrance_side_point: Optional[Dict[str, float]] = None
) -> Optional[Dict[str, Any]]:
    """
    Process a person centroid event and detect line crossings.
    
    Args:
        db: Database session
        camera_id: Camera ID
        track_id: Track ID of the person
        centroid_x: X coordinate of person centroid
        centroid_y: Y coordinate of person centroid
        line_config: Line definition {'x1': float, 'y1': float, 'x2': float, 'y2': float}
        direction_filter: Which directions to count ("in", "out", "both")
        timestamp: Event timestamp (defaults to current time)
    
    Returns:
        Event dict if crossing detected, None otherwise
        Format: {"camera_id": int, "event": "enter"|"exit", "timestamp": float, "track_id": int}
    """
    if timestamp is None:
        timestamp = time.time()
    
    # Get previous position for this track
    prev_position = track_positions.get(track_id)
    
    # Update current position
    current_position = {
        'x': centroid_x,
        'y': centroid_y,
        'timestamp': timestamp
    }
    track_positions[track_id] = current_position
    
    # Need previous position to detect crossing
    if prev_position is None:
        return None
    
    # Detect line crossing
    prev_point = {'x': prev_position['x'], 'y': prev_position['y']}
    curr_point = {'x': centroid_x, 'y': centroid_y}
    
    direction = detect_line_crossing(prev_point, curr_point, line_config)
    
    if direction is None:
        return None
    
    # Map direction to event type
    # If entrance_side_point is provided, use it to determine enter/exit
    # Otherwise, use geometric direction (IN = enter, OUT = exit)
    if entrance_side_point:
        # Determine which side the person is coming from (previous position)
        prev_side = get_point_side_of_line(prev_point, line_config)
        entrance_side = get_point_side_of_line(entrance_side_point, line_config)
        
        if prev_side and entrance_side:
            # If coming from the entrance side, it's an enter event
            # If coming from the opposite side, it's an exit event
            if prev_side == entrance_side:
                event_type = "enter"
            else:
                event_type = "exit"
        else:
            # Fallback to geometric direction if sides can't be determined
            event_type = "enter" if direction == "IN" else "exit"
    else:
        # No entrance side specified - use geometric direction
        # IN means entering (crossing from right to left relative to line direction)
        # OUT means exiting (crossing from left to right relative to line direction)
        event_type = "enter" if direction == "IN" else "exit"
    
    # Apply direction filter
    if direction_filter == "in" and event_type != "enter":
        return None
    if direction_filter == "out" and event_type != "exit":
        return None
    
    # Apply debounce
    if not should_count_crossing(track_id, direction, timestamp):
        return None
    
    # Create event
    event_data = {
        "camera_id": camera_id,
        "event": event_type,
        "timestamp": datetime.fromtimestamp(timestamp),
        "track_id": track_id
    }
    
    # Persist to database
    from app.db.schemas.entry_exit_event import EntryExitEventCreate
    event_create = EntryExitEventCreate(**event_data)
    db_event = create_entry_exit_event(db, event_create)
    
    # Log the event
    print(f"🚪 ENTRANCE/EXIT EVENT: camera_id={camera_id}, event={event_type}, track_id={track_id}, timestamp={int(timestamp)}")
    
    # Return event for real-time processing
    return {
        "camera_id": camera_id,
        "event": event_type,
        "timestamp": int(timestamp),
        "track_id": track_id
    }


def clear_track_position(track_id: int):
    """Clear the stored position for a track (e.g., when track ends)"""
    if track_id in track_positions:
        del track_positions[track_id]


def clear_all_track_positions():
    """Clear all stored track positions"""
    track_positions.clear()


def get_track_position(track_id: int) -> Optional[Dict[str, Any]]:
    """Get the current position for a track"""
    return track_positions.get(track_id)

