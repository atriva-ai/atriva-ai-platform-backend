# Vehicle Tracking with ByteTrack Algorithm

This document describes the new vehicle tracking functionality that replaces the existing AI License Plate Recognition system. The new system uses the ByteTrack algorithm with YOLOv8n for vehicle detection and tracking.

## Overview

The vehicle tracking system provides:
- **Vehicle Detection**: Uses YOLOv8n to detect vehicles (cars, motorcycles, buses, trucks)
- **Multi-Object Tracking**: Implements ByteTrack algorithm for robust vehicle tracking
- **Annotated Frames**: Saves frames with bounding boxes and track IDs
- **Configurable**: Can be enabled/disabled per camera with customizable parameters

## Features

- **Disabled by Default**: Vehicle tracking is disabled by default for new cameras
- **Manual Enable**: Must be manually enabled in camera settings
- **Real-time Processing**: Processes frames in real-time when enabled
- **Frame Storage**: Saves annotated frames to camera-specific folders
- **Live View Integration**: Shows annotated frames in live view when tracking is active

## Architecture

### Components

1. **VehicleTracker**: Main service class managing tracking for each camera
2. **ByteTracker**: Implementation of the ByteTrack algorithm
3. **YOLOv8n Integration**: Vehicle detection using pre-trained models
4. **Frame Processing**: Real-time frame annotation and storage

### Data Flow

```
Camera Stream → Frame Decode → Vehicle Detection → ByteTrack → Annotated Frame → Storage + Live View
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download YOLOv8n Models

```bash
./download_models.sh
```

This will download:
- `yolov8n.onnx` - ONNX format (preferred)
- `yolov8n.weights` - Darknet weights (fallback)
- `yolov8n.cfg` - Model configuration

### 3. Run Database Migration

```bash
python -m app.db.migrations.add_vehicle_tracking
```

## Configuration

### Camera Settings

Each camera can have the following vehicle tracking settings:

```json
{
  "vehicle_tracking_enabled": false,
  "vehicle_tracking_config": {
    "track_thresh": 0.5,
    "track_buffer": 30,
    "match_thresh": 0.8
  }
}
```

### Configuration Parameters

- **track_thresh**: Confidence threshold for detection (0.0-1.0)
- **track_buffer**: Number of frames to keep lost tracks (default: 30)
- **match_thresh**: IoU threshold for track association (0.0-1.0)

## API Endpoints

### Enable/Disable Vehicle Tracking

```http
PUT /api/v1/cameras/{camera_id}/vehicle-tracking/enable/
PUT /api/v1/cameras/{camera_id}/vehicle-tracking/disable/
```

### Start/Stop Tracking

```http
POST /api/v1/cameras/{camera_id}/vehicle-tracking/start/
POST /api/v1/cameras/{camera_id}/vehicle-tracking/stop/
```

### Configuration Management

```http
PUT /api/v1/cameras/{camera_id}/vehicle-tracking/config/
GET /api/v1/cameras/{camera_id}/vehicle-tracking/status/
```

### Enhanced Frame Retrieval

```http
GET /api/v1/cameras/{camera_id}/latest-frame/?use_tracking=true
```

## Usage Examples

### 1. Enable Vehicle Tracking for a Camera

```bash
# Enable tracking
curl -X PUT "http://localhost:8000/api/v1/cameras/1/vehicle-tracking/enable/"

# Configure tracking parameters
curl -X PUT "http://localhost:8000/api/v1/cameras/1/vehicle-tracking/config/" \
  -H "Content-Type: application/json" \
  -d '{
    "track_thresh": 0.6,
    "track_buffer": 25,
    "match_thresh": 0.7
  }'

# Start tracking
curl -X POST "http://localhost:8000/api/v1/cameras/1/vehicle-tracking/start/"
```

### 2. Get Annotated Frames

```bash
# Get frame with vehicle tracking (if enabled)
curl "http://localhost:8000/api/v1/cameras/1/latest-frame/?use_tracking=true" \
  -o tracked_frame.jpg

# Get regular frame without tracking
curl "http://localhost:8000/api/v1/cameras/1/latest-frame/" \
  -o regular_frame.jpg
```

### 3. Check Tracking Status

```bash
curl "http://localhost:8000/api/v1/cameras/1/vehicle-tracking/status/"
```

## File Storage

### Annotated Frame Storage

Annotated frames are saved to:
```
/tmp/vehicle_tracking/camera_{camera_id}/
```

### File Naming Convention

```
frame_{frame_number:06d}_{timestamp}.jpg
```

Example: `frame_000001_1640995200.jpg`

### Cleanup

- Frames older than 1 hour are automatically cleaned up
- Manual cleanup available via API endpoints
- Storage space is managed per camera

## Integration with Live View

### Frame Processing Pipeline

1. **Decode Frame**: Get raw frame from video pipeline
2. **Vehicle Detection**: Run YOLOv8n inference
3. **Track Update**: Update ByteTrack with new detections
4. **Frame Annotation**: Draw bounding boxes and track IDs
5. **Storage**: Save annotated frame to camera folder
6. **Live View**: Return annotated frame for display

### Headers in Response

When vehicle tracking is active, the frame response includes:

```
X-Vehicle-Tracking: enabled
X-Tracked-Vehicles: 3
```

## Performance Considerations

### Hardware Requirements

- **CPU**: Multi-core processor recommended
- **Memory**: 2GB+ RAM for model loading
- **Storage**: SSD recommended for frame storage

### Optimization Tips

1. **Adjust FPS**: Lower frame rate for better performance
2. **Model Selection**: Use ONNX format when possible
3. **Confidence Thresholds**: Higher thresholds reduce false positives
4. **Track Buffer**: Smaller buffers use less memory

## Troubleshooting

### Common Issues

1. **Model Loading Failed**
   - Check if model files exist in `models/` directory
   - Verify file permissions and paths
   - Try fallback to OpenCV DNN

2. **Tracking Not Working**
   - Verify vehicle tracking is enabled for the camera
   - Check tracking configuration parameters
   - Monitor logs for errors

3. **Performance Issues**
   - Reduce frame processing rate
   - Adjust confidence thresholds
   - Check system resources

### Debug Information

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

```bash
# Check tracking status
curl "http://localhost:8000/api/v1/cameras/{camera_id}/vehicle-tracking/status/"

# Check frame availability
curl "http://localhost:8000/api/v1/cameras/{camera_id}/latest-frame/"
```

## Migration from License Plate Recognition

### What Changed

- **Replaced**: AI License Plate Recognition system
- **Added**: Vehicle tracking with ByteTrack algorithm
- **Enhanced**: Frame annotation and storage capabilities
- **Improved**: Real-time processing and live view integration

### Migration Steps

1. **Update Database Schema**: Run migration script
2. **Install Dependencies**: Add OpenCV, NumPy, SciPy
3. **Download Models**: Get YOLOv8n model files
4. **Configure Cameras**: Enable tracking per camera as needed
5. **Update Frontend**: Modify UI to show tracking options

## Future Enhancements

### Planned Features

- **Multi-Camera Tracking**: Cross-camera vehicle re-identification
- **Advanced Analytics**: Vehicle counting, speed estimation
- **Alert System**: Configurable alerts for specific events
- **Export Options**: Video export with tracking overlays
- **Web Interface**: Real-time tracking visualization

### Extensibility

The system is designed to be easily extensible:
- **New Models**: Support for different detection models
- **Tracking Algorithms**: Plug-in architecture for tracking methods
- **Output Formats**: Configurable annotation styles
- **Storage Backends**: Support for different storage systems

## Support

For issues and questions:
1. Check the logs for error messages
2. Verify configuration parameters
3. Test with different camera streams
4. Review performance metrics

## License

This vehicle tracking system is part of the Atriva Mobile LP Recorder App.
