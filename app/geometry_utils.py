"""
Geometry utility functions for line crossing detection and other spatial calculations.
"""

from typing import Dict, Optional, Any
import time

# Debounce configuration
MIN_CROSS_INTERVAL = 3.0  # seconds - minimum time between valid crossings for the same track

# In-memory track state for debouncing
# Structure: {track_id: {"last_cross_time": float, "last_direction": "IN" | "OUT"}}
track_state: Dict[int, Dict[str, Any]] = {}


def detect_line_crossing(
    prev_point: Dict[str, float],
    curr_point: Dict[str, float],
    line: Dict[str, float]
) -> Optional[str]:
    """
    Detect if a point has crossed a line and determine the direction.
    
    Args:
        prev_point: Previous point coordinates as {'x': float, 'y': float}
        curr_point: Current point coordinates as {'x': float, 'y': float}
        line: Line definition as {'x1': float, 'y1': float, 'x2': float, 'y2': float}
              The line goes from (x1, y1) to (x2, y2)
    
    Returns:
        "IN" if crossing from right side to left side (relative to line direction)
        "OUT" if crossing from left side to right side (relative to line direction)
        None if no crossing occurred
    
    Algorithm:
        Uses cross product to determine which side of the line each point is on.
        If points are on opposite sides, a crossing occurred.
        Direction is determined by the order of the cross products.
    """
    # Extract line endpoints
    x1, y1 = line['x1'], line['y1']
    x2, y2 = line['x2'], line['y2']
    
    # Extract point coordinates
    prev_x, prev_y = prev_point['x'], prev_point['y']
    curr_x, curr_y = curr_point['x'], curr_point['y']
    
    # Calculate cross product to determine which side of the line each point is on
    # Cross product: (x2-x1)*(y-y1) - (y2-y1)*(x-x1)
    # Positive = left side (relative to line direction from (x1,y1) to (x2,y2))
    # Negative = right side
    
    # Vector from line start to line end
    line_dx = x2 - x1
    line_dy = y2 - y1
    
    # Cross product for previous point
    # (line_dx, line_dy) × (prev_x - x1, prev_y - y1)
    prev_cross = line_dx * (prev_y - y1) - line_dy * (prev_x - x1)
    
    # Cross product for current point
    # (line_dx, line_dy) × (curr_x - x1, curr_y - y1)
    curr_cross = line_dx * (curr_y - y1) - line_dy * (curr_x - x1)
    
    # Check if points are on opposite sides of the line
    # A crossing occurs when the cross products have opposite signs
    if prev_cross * curr_cross >= 0:
        # Same side or on the line - no crossing
        return None
    
    # Crossing detected - determine direction
    # If prev_cross > 0 (left side) and curr_cross < 0 (right side) -> moving OUT
    # If prev_cross < 0 (right side) and curr_cross > 0 (left side) -> moving IN
    if prev_cross > 0 and curr_cross < 0:
        return "OUT"
    elif prev_cross < 0 and curr_cross > 0:
        return "IN"
    
    # Edge case: one point exactly on the line (cross product = 0)
    # This shouldn't happen with the >= 0 check above, but handle it anyway
    return None


def get_point_side_of_line(point: Dict[str, float], line: Dict[str, float]) -> Optional[str]:
    """
    Determine which side of a line a point is on.
    
    Args:
        point: Point coordinates as {'x': float, 'y': float}
        line: Line definition as {'x1': float, 'y1': float, 'x2': float, 'y2': float}
              The line goes from (x1, y1) to (x2, y2)
    
    Returns:
        "left" if point is on the left side (positive cross product)
        "right" if point is on the right side (negative cross product)
        None if point is exactly on the line
    """
    x1, y1 = line['x1'], line['y1']
    x2, y2 = line['x2'], line['y2']
    px, py = point['x'], point['y']
    
    # Vector from line start to line end
    line_dx = x2 - x1
    line_dy = y2 - y1
    
    # Cross product: (line_dx, line_dy) × (px - x1, py - y1)
    cross = line_dx * (py - y1) - line_dy * (px - x1)
    
    if cross > 0:
        return "left"
    elif cross < 0:
        return "right"
    else:
        return None


def should_count_crossing(track_id: int, direction: str, current_time: Optional[float] = None) -> bool:
    """
    Determine if a crossing should be counted based on debounce logic.
    
    Prevents double-counting when a tracked person:
    - Hesitates near entrance
    - Crosses back and forth briefly
    
    Key principle: Debounce is per track_id, not global.
    
    Args:
        track_id: The unique track ID for the person
        direction: The crossing direction ("IN" or "OUT")
        current_time: Current timestamp (defaults to time.time() if not provided)
    
    Returns:
        True if the crossing should be counted, False if it should be ignored
    
    Logic:
        - If (now - last_cross_time[track_id]) < MIN_CROSS_INTERVAL: ignore
        - If direction == last_direction[track_id]: ignore (same direction as last)
        - Otherwise: count and update state
    """
    if current_time is None:
        current_time = time.time()
    
    # Normalize direction to uppercase
    direction = direction.upper()
    if direction not in ("IN", "OUT"):
        return False
    
    # Get or initialize track state
    if track_id not in track_state:
        # First crossing for this track - always count
        track_state[track_id] = {
            "last_cross_time": current_time,
            "last_direction": direction
        }
        return True
    
    state = track_state[track_id]
    last_cross_time = state.get("last_cross_time", 0.0)
    last_direction = state.get("last_direction")
    
    # Check time interval
    time_since_last = current_time - last_cross_time
    if time_since_last < MIN_CROSS_INTERVAL:
        # Too soon after last crossing - ignore
        return False
    
    # Check if same direction as last crossing
    if direction == last_direction:
        # Same direction as last - ignore (likely hesitation or back-and-forth)
        return False
    
    # Valid crossing - update state and count
    track_state[track_id] = {
        "last_cross_time": current_time,
        "last_direction": direction
    }
    return True


def reset_track_state(track_id: int):
    """
    Reset the debounce state for a specific track.
    
    Useful when a track ends or is removed.
    
    Args:
        track_id: The track ID to reset
    """
    if track_id in track_state:
        del track_state[track_id]


def clear_all_track_states():
    """
    Clear all track debounce states.
    
    Useful for cleanup or when resetting the system.
    """
    track_state.clear()


def get_track_state(track_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the current debounce state for a track.
    
    Args:
        track_id: The track ID to query
    
    Returns:
        Dictionary with "last_cross_time" and "last_direction", or None if track not found
    """
    return track_state.get(track_id)

