#!/usr/bin/env python3
"""
Test script for backend vehicle tracking proxy functionality
"""

import requests
import json
import time
import sys
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8000"
AI_SERVICE_URL = "http://localhost:8001"
CAMERA_ID = 1

def test_backend_proxy():
    """Test the backend proxy functionality for vehicle tracking"""
    
    print("🚗 Testing Backend Vehicle Tracking Proxy")
    print("=" * 60)
    
    # Test 1: Check if camera exists
    print("\n1. Checking camera existence...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}")
        if response.status_code == 200:
            camera = response.json()
            print(f"✅ Camera found: {camera['name']}")
            print(f"   Vehicle tracking enabled: {camera.get('vehicle_tracking_enabled', False)}")
        else:
            print(f"❌ Camera not found: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking camera: {e}")
        return False
    
    # Test 2: Enable vehicle tracking
    print("\n2. Enabling vehicle tracking...")
    try:
        response = requests.put(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/vehicle-tracking/enable/")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Vehicle tracking enabled: {result['message']}")
        else:
            print(f"❌ Failed to enable tracking: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error enabling tracking: {e}")
        return False
    
    # Test 3: Configure tracking parameters
    print("\n3. Configuring tracking parameters...")
    try:
        config = {
            "track_thresh": 0.5,
            "track_buffer": 30,
            "match_thresh": 0.8
        }
        response = requests.put(
            f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/vehicle-tracking/config/",
            json=config
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Configuration updated: {result['message']}")
        else:
            print(f"❌ Failed to update config: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False
    
    # Test 4: Start vehicle tracking (proxy to AI service)
    print("\n4. Starting vehicle tracking via backend proxy...")
    try:
        response = requests.post(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/vehicle-tracking/start/")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Tracking started: {result['message']}")
        else:
            print(f"❌ Failed to start tracking: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error starting tracking: {e}")
        return False
    
    # Test 5: Check tracking status (proxy to AI service)
    print("\n5. Checking tracking status via backend proxy...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/vehicle-tracking/status/")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Tracking status: {status['tracking_enabled']}")
            print(f"   Tracker status: {status.get('tracker_status', {})}")
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return False
    
    # Test 6: Get frame with tracking (proxy to AI service)
    print("\n6. Getting frame with vehicle tracking via backend proxy...")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/latest-frame/",
            params={"use_tracking": "true"}
        )
        if response.status_code == 200:
            # Check headers for tracking information
            tracking_enabled = response.headers.get('X-Vehicle-Tracking', 'disabled')
            tracked_vehicles = response.headers.get('X-Tracked-Vehicles', '0')
            saved_path = response.headers.get('X-Saved-Path', '')
            
            print(f"✅ Frame retrieved with tracking: {tracking_enabled}")
            print(f"   Tracked vehicles: {tracked_vehicles}")
            print(f"   Saved path: {saved_path}")
            
            # Save the frame for inspection
            output_file = f"backend_tracked_frame_{CAMERA_ID}.jpg"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"   Frame saved as: {output_file}")
        else:
            print(f"❌ Failed to get frame: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting frame: {e}")
        return False
    
    # Test 7: Get regular frame without tracking
    print("\n7. Getting regular frame without tracking...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/latest-frame/")
        if response.status_code == 200:
            output_file = f"backend_regular_frame_{CAMERA_ID}.jpg"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✅ Regular frame saved as: {output_file}")
        else:
            print(f"❌ Failed to get regular frame: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting regular frame: {e}")
        return False
    
    # Test 8: Stop tracking (proxy to AI service)
    print("\n8. Stopping vehicle tracking via backend proxy...")
    try:
        response = requests.post(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/vehicle-tracking/stop/")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Tracking stopped: {result['message']}")
        else:
            print(f"❌ Failed to stop tracking: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error stopping tracking: {e}")
        return False
    
    # Test 9: Disable vehicle tracking
    print("\n9. Disabling vehicle tracking...")
    try:
        response = requests.put(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/vehicle-tracking/disable/")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Vehicle tracking disabled: {result['message']}")
        else:
            print(f"❌ Failed to disable tracking: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error disabling tracking: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All backend proxy tests completed successfully!")
    print("\nGenerated files:")
    print(f"  - backend_tracked_frame_{CAMERA_ID}.jpg (with vehicle tracking)")
    print(f"  - backend_regular_frame_{CAMERA_ID}.jpg (without tracking)")
    
    return True

def test_error_handling():
    """Test error handling scenarios"""
    
    print("\n🔍 Testing Error Handling")
    print("=" * 60)
    
    # Test 1: Try to start tracking on non-existent camera
    print("\n1. Testing non-existent camera...")
    try:
        response = requests.post(f"{BACKEND_URL}/api/v1/cameras/999/vehicle-tracking/start/")
        if response.status_code == 404:
            print("✅ Correctly handled non-existent camera")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Try to start tracking without enabling first
    print("\n2. Testing tracking without enabling...")
    try:
        # First disable tracking
        requests.put(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/vehicle-tracking/disable/")
        
        # Try to start tracking
        response = requests.post(f"{BACKEND_URL}/api/v1/cameras/{CAMERA_ID}/vehicle-tracking/start/")
        if response.status_code == 400:
            print("✅ Correctly handled tracking not enabled")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✅ Error handling tests completed!")

def test_ai_service_connectivity():
    """Test direct AI service connectivity"""
    
    print("\n🔗 Testing AI Service Connectivity")
    print("=" * 60)
    
    # Test 1: Check AI service health
    print("\n1. Checking AI service health...")
    try:
        response = requests.get(f"{AI_SERVICE_URL}/models", timeout=5)
        if response.status_code == 200:
            print("✅ AI service is accessible")
        else:
            print(f"⚠️  AI service responded with: {response.status_code}")
    except Exception as e:
        print(f"❌ AI service is not accessible: {e}")
    
    # Test 2: Check vehicle tracking endpoints
    print("\n2. Checking vehicle tracking endpoints...")
    try:
        response = requests.get(f"{AI_SERVICE_URL}/vehicle-tracking/status/{CAMERA_ID}", timeout=5)
        if response.status_code == 200:
            print("✅ Vehicle tracking endpoints are accessible")
        else:
            print(f"⚠️  Vehicle tracking endpoints responded with: {response.status_code}")
    except Exception as e:
        print(f"❌ Vehicle tracking endpoints are not accessible: {e}")
    
    print("\n✅ AI service connectivity tests completed!")

if __name__ == "__main__":
    print("Backend Vehicle Tracking Proxy Test Suite")
    print("Make sure the backend API server is running on localhost:8000")
    print("Make sure the AI service is running on localhost:8001")
    print("Make sure you have at least one camera configured")
    
    try:
        # Test AI service connectivity first
        test_ai_service_connectivity()
        
        # Run main tests
        success = test_backend_proxy()
        
        if success:
            # Run error handling tests
            test_error_handling()
        
        print("\n🎉 Test suite completed!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
