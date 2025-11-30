"""
Analytics type constants and configurations
"""

from enum import Enum
from typing import Dict, Any

class AnalyticsType(str, Enum):
    PEOPLE_COUNTING = "people_counting"
    DWELL_TIME = "dwell_time"
    DEMOGRAPHIC = "demographic"
    PEOPLE_COUNTING_BY_ZONE = "people_counting_by_zone"
    DWELL_TIME_BY_ZONE = "dwell_time_by_zone"
    LINE_CROSS_COUNT = "line_cross_count"
    DEMOGRAPHIC_ON_LINE_CROSSING = "demographic_on_line_crossing"

class AnalyticsConfig:
    """Predefined analytics configurations"""
    
    PEOPLE_COUNTING = {
        "name": "People Counting",
        "type": AnalyticsType.PEOPLE_COUNTING,
        "description": "Count the number of people entering and exiting areas (whole camera)",
        "default_config": {
            "threshold": 0.5,
            "min_height": 100,
            "max_height": 300,
            "tracking_enabled": True,
            "count_direction": "both",  # "in", "out", "both"
            "reset_interval": 3600  # seconds
        },
        "requires_zone": False,
        "requires_line": False
    }
    
    DWELL_TIME = {
        "name": "Dwell Time Analysis",
        "type": AnalyticsType.DWELL_TIME,
        "description": "Analyze how long people spend in specific areas (whole camera)",
        "default_config": {
            "min_dwell_time": 5,  # seconds
            "max_dwell_time": 300,  # seconds
            "heatmap_enabled": True,
            "tracking_interval": 1,  # seconds
            "session_timeout": 30  # seconds
        },
        "requires_zone": False,
        "requires_line": False
    }
    
    DEMOGRAPHIC = {
        "name": "Demographic Analytics",
        "type": AnalyticsType.DEMOGRAPHIC,
        "description": "Analyze demographic information of visitors (whole camera)",
        "default_config": {
            "age_groups": ["18-25", "26-35", "36-45", "46-55", "55+"],
            "gender_detection": True,
            "emotion_analysis": True,
            "privacy_mode": True,
            "confidence_threshold": 0.7,
            "anonymize_data": True
        },
        "requires_zone": False,
        "requires_line": False
    }

    PEOPLE_COUNTING_BY_ZONE = {
        "name": "People Counting by Zone",
        "type": AnalyticsType.PEOPLE_COUNTING_BY_ZONE,
        "description": "Count people within a defined zone area",
        "default_config": {
            "threshold": 0.5,
            "min_height": 100,
            "max_height": 300,
            "tracking_enabled": True,
            "count_interval": 1,  # seconds
            "max_occupancy": 100,
            "zone_required": True
        },
        "requires_zone": True,
        "requires_line": False
    }

    DWELL_TIME_BY_ZONE = {
        "name": "Dwell Time Analysis by Zone",
        "type": AnalyticsType.DWELL_TIME_BY_ZONE,
        "description": "Track dwell time within a defined zone",
        "default_config": {
            "min_dwell_time": 5,  # seconds
            "max_dwell_time": 300,  # seconds
            "tracking_interval": 1,  # seconds
            "session_timeout": 30,  # seconds
            "heatmap_enabled": True,
            "zone_required": True
        },
        "requires_zone": True,
        "requires_line": False
    }

    LINE_CROSS_COUNT = {
        "name": "Line Cross Count",
        "type": AnalyticsType.LINE_CROSS_COUNT,
        "description": "Count people crossing a virtual line",
        "default_config": {
            "threshold": 0.5,
            "min_height": 100,
            "max_height": 300,
            "tracking_enabled": True,
            "line_required": True,
            "count_direction": "both",  # "in", "out", "both"
            "reset_interval": 3600  # seconds
        },
        "requires_zone": False,
        "requires_line": True
    }

    DEMOGRAPHIC_ON_LINE_CROSSING = {
        "name": "Demographic Analysis on Line Crossing",
        "type": AnalyticsType.DEMOGRAPHIC_ON_LINE_CROSSING,
        "description": "Analyze demographics of people crossing a line",
        "default_config": {
            "threshold": 0.5,
            "min_height": 100,
            "max_height": 300,
            "tracking_enabled": True,
            "line_required": True,
            "age_groups": ["18-25", "26-35", "36-45", "46-55", "55+"],
            "gender_detection": True,
            "emotion_analysis": True,
            "privacy_mode": True,
            "confidence_threshold": 0.7,
            "anonymize_data": True
        },
        "requires_zone": False,
        "requires_line": True
    }

def get_analytics_config(analytics_type: AnalyticsType) -> Dict[str, Any]:
    """Get configuration for a specific analytics type"""
    configs = {
        AnalyticsType.PEOPLE_COUNTING: AnalyticsConfig.PEOPLE_COUNTING,
        AnalyticsType.DWELL_TIME: AnalyticsConfig.DWELL_TIME,
        AnalyticsType.DEMOGRAPHIC: AnalyticsConfig.DEMOGRAPHIC,
        AnalyticsType.PEOPLE_COUNTING_BY_ZONE: AnalyticsConfig.PEOPLE_COUNTING_BY_ZONE,
        AnalyticsType.DWELL_TIME_BY_ZONE: AnalyticsConfig.DWELL_TIME_BY_ZONE,
        AnalyticsType.LINE_CROSS_COUNT: AnalyticsConfig.LINE_CROSS_COUNT,
        AnalyticsType.DEMOGRAPHIC_ON_LINE_CROSSING: AnalyticsConfig.DEMOGRAPHIC_ON_LINE_CROSSING,
    }
    return configs.get(analytics_type, {})

def get_all_analytics_configs() -> Dict[str, Dict[str, Any]]:
    """Get all predefined analytics configurations"""
    return {
        AnalyticsType.PEOPLE_COUNTING: AnalyticsConfig.PEOPLE_COUNTING,
        AnalyticsType.DWELL_TIME: AnalyticsConfig.DWELL_TIME,
        AnalyticsType.DEMOGRAPHIC: AnalyticsConfig.DEMOGRAPHIC,
        AnalyticsType.PEOPLE_COUNTING_BY_ZONE: AnalyticsConfig.PEOPLE_COUNTING_BY_ZONE,
        AnalyticsType.DWELL_TIME_BY_ZONE: AnalyticsConfig.DWELL_TIME_BY_ZONE,
        AnalyticsType.LINE_CROSS_COUNT: AnalyticsConfig.LINE_CROSS_COUNT,
        AnalyticsType.DEMOGRAPHIC_ON_LINE_CROSSING: AnalyticsConfig.DEMOGRAPHIC_ON_LINE_CROSSING,
    } 