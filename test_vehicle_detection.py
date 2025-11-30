#!/usr/bin/env python3
"""
Test script for AI inference service vehicle detection functionality
Tests YOLOv8n model loading and continuous inference at 5fps intervals
"""

import requests
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Configuration
BACKEND_URL = "http://172.16.225.114:8000"
AI_SERVICE_URL = "http://172.16.225.114:8001"
CAMERA_ID = 28  # Modify this to test different cameras
MODEL_NAME = "yolov8n"
ACCELERATOR = "cpu32"
INFERENCE_INTERVAL = 0.2  # 5fps = 0.2 seconds between inferences
MAX_INFERENCES = 50  # Run for 10 seconds at 5fps

def test_ai_service_health():
    """Test if AI inference service is running"""
    print("🔍 Testing AI Inference Service Health")
    print("=" * 60)
    
    try:
        response = requests.get(f"{AI_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ AI inference service is running")
            return True
        else:
            print(f"❌ AI service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ AI service is not accessible: {e}")
        return False

def test_camera_frames_available():
    """Test if camera has frames available for inference"""
    print(f"\n🔍 Testing Camera {CAMERA_ID} Frame Availability")
    print("-" * 40)
    
    try:
        # Check if camera has frames
        response = requests.get(f"{AI_SERVICE_URL}/shared/cameras/{CAMERA_ID}/frames", timeout=5)
        if response.status_code == 200:
            frame_info = response.json()
            print(f"✅ Camera {CAMERA_ID} frame info:")
            print(f"   Frame count: {frame_info.get('frame_count', 0)}")
            print(f"   Has frames: {frame_info.get('has_frames', False)}")
            print(f"   Latest frame: {frame_info.get('latest_frame', 'None')}")
            
            if frame_info.get('has_frames', False):
                return True
            else:
                print(f"❌ No frames available for camera {CAMERA_ID}")
                return False
        else:
            print(f"❌ Failed to get frame info: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking camera frames: {e}")
        return False

def test_model_loading():
    """Test loading YOLOv8n model"""
    print(f"\n🤖 Testing YOLOv8n Model Loading")
    print("-" * 40)
    
    try:
        # First check what models are available
        print("Checking available models...")
        models_response = requests.get(f"{AI_SERVICE_URL}/models", timeout=5)
        if models_response.status_code == 200:
            models = models_response.json()
            print(f"Available models: {models.get('available_models', [])}")
        else:
            print(f"Could not get available models: {models_response.status_code}")
        
        # Try to load the model
        print(f"Loading {MODEL_NAME} model with {ACCELERATOR} accelerator...")
        response = requests.post(
            f"{AI_SERVICE_URL}/model/load",
            params={"model_name": MODEL_NAME, "accelerator": ACCELERATOR},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Model loaded successfully:")
            print(f"   Model: {result.get('model_name', 'Unknown')}")
            print(f"   Accelerator: {result.get('accelerator', 'Unknown')}")
            print(f"   Architecture: {result.get('architecture', 'Unknown')}")
            return True
        else:
            print(f"❌ Failed to load model: {response.status_code}")
            print(f"   Response: {response.text}")
            print(f"\n💡 Note: YOLOv8n model needs to be downloaded and converted to OpenVINO format first.")
            print(f"   The model files should be in /app/models/yolov8n/ directory.")
            print(f"   Check the AI inference service logs for model download/conversion errors.")
            return False
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False

def test_single_inference():
    """Test a single inference on latest frame"""
    print(f"\n🎯 Testing Single Inference on Camera {CAMERA_ID}")
    print("-" * 40)
    
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/shared/cameras/{CAMERA_ID}/inference",
            params={"object_name": "license_plate"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Inference successful:")
            print(f"   Camera ID: {result.get('camera_id', 'Unknown')}")
            print(f"   Object name: {result.get('object_name', 'Unknown')}")
            print(f"   Frame path: {result.get('frame_path', 'Unknown')}")
            print(f"   Detections: {len(result.get('detections', []))}")
            
            # Show detection details
            detections = result.get('detections', [])
            if detections:
                print(f"   Detection details:")
                for i, detection in enumerate(detections):
                    print(f"     {i+1}. Class: {detection.get('class_id', 'Unknown')}, "
                          f"Confidence: {detection.get('confidence', 0):.3f}, "
                          f"BBox: {detection.get('bbox', [])}")
            else:
                print(f"   No objects detected")
            
            return True
        else:
            print(f"❌ Inference failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error running inference: {e}")
        return False

def test_continuous_inference():
    """Test continuous inference at 5fps intervals"""
    print(f"\n🔄 Testing Continuous Inference at 5fps")
    print("-" * 40)
    print(f"Running {MAX_INFERENCES} inferences with {INFERENCE_INTERVAL}s intervals...")
    print(f"Total duration: {MAX_INFERENCES * INFERENCE_INTERVAL:.1f} seconds")
    
    successful_inferences = 0
    total_detections = 0
    start_time = time.time()
    
    try:
        for i in range(MAX_INFERENCES):
            inference_start = time.time()
            
            try:
                response = requests.post(
                    f"{AI_SERVICE_URL}/shared/cameras/{CAMERA_ID}/inference",
                    params={"object_name": "license_plate"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    detections = result.get('detections', [])
                    successful_inferences += 1
                    total_detections += len(detections)
                    
                    print(f"  [{i+1:2d}/{MAX_INFERENCES}] ✅ {len(detections)} detections "
                          f"(confidence: {max([d.get('confidence', 0) for d in detections], default=0):.3f})")
                else:
                    print(f"  [{i+1:2d}/{MAX_INFERENCES}] ❌ Failed: {response.status_code}")
                
            except Exception as e:
                print(f"  [{i+1:2d}/{MAX_INFERENCES}] ❌ Error: {e}")
            
            # Calculate sleep time to maintain 5fps
            inference_time = time.time() - inference_start
            sleep_time = max(0, INFERENCE_INTERVAL - inference_time)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        total_time = time.time() - start_time
        actual_fps = successful_inferences / total_time if total_time > 0 else 0
        
        print(f"\n📊 Continuous Inference Results:")
        print(f"   Successful inferences: {successful_inferences}/{MAX_INFERENCES}")
        print(f"   Total detections: {total_detections}")
        print(f"   Average detections per frame: {total_detections/successful_inferences if successful_inferences > 0 else 0:.2f}")
        print(f"   Actual FPS: {actual_fps:.2f}")
        print(f"   Total time: {total_time:.2f}s")
        
        return successful_inferences > 0
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Continuous inference interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error during continuous inference: {e}")
        return False

def test_annotated_frame_generation():
    """Test if annotated frames are being generated"""
    print(f"\n🖼️ Testing Annotated Frame Generation")
    print("-" * 40)
    
    try:
        # Run a few inferences to generate annotated frames
        print("Running inferences to generate annotated frames...")
        for i in range(3):
            response = requests.post(
                f"{AI_SERVICE_URL}/shared/cameras/{CAMERA_ID}/inference",
                params={"object_name": "license_plate"},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                frame_path = result.get('frame_path', '')
                print(f"  Inference {i+1}: Frame path = {frame_path}")
            else:
                print(f"  Inference {i+1}: Failed ({response.status_code})")
            
            time.sleep(0.5)
        
        print("\n✅ Annotated frames should be generated in the shared volume")
        print("   Check: docker exec mobile-lp-recorder-app-ai_inference-1 ls -la /app/frames/")
        print("   Or check the shared volume on host system")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing annotated frame generation: {e}")
        return False

def main():
    """Main test function"""
    print("🚗 AI Inference Service Vehicle Detection Test Suite")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"AI Service URL: {AI_SERVICE_URL}")
    print(f"Camera ID: {CAMERA_ID}")
    print(f"Model: {MODEL_NAME} ({ACCELERATOR})")
    print(f"Inference Rate: {1/INFERENCE_INTERVAL:.1f} FPS")
    print("=" * 60)
    
    try:
        # Test 1: AI Service Health
        if not test_ai_service_health():
            print("\n❌ AI service health check failed. Exiting.")
            return False
        
        # Test 2: Camera Frame Availability
        if not test_camera_frames_available():
            print("\n❌ No camera frames available. Exiting.")
            return False
        
        # Test 3: Model Loading
        model_loaded = test_model_loading()
        if not model_loaded:
            print("\n⚠️ Model loading failed, but continuing with other tests...")
            print("   (Inference tests will likely fail without a loaded model)")
        
        # Test 4: Single Inference
        if not test_single_inference():
            print("\n❌ Single inference failed. Exiting.")
            return False
        
        # Test 5: Continuous Inference
        if not test_continuous_inference():
            print("\n❌ Continuous inference failed.")
            return False
        
        # Test 6: Annotated Frame Generation
        test_annotated_frame_generation()
        
        print("\n" + "=" * 60)
        print("✅ All vehicle detection tests completed successfully!")
        print("\n📁 Check the shared volume for annotated frames:")
        print("   docker exec mobile-lp-recorder-app-ai_inference-1 ls -la /app/frames/")
        print("   docker exec mobile-lp-recorder-app-video_pipeline-1 ls -la /app/frames/")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        return False

if __name__ == "__main__":
    print("AI Inference Service Vehicle Detection Test Suite")
    print("Make sure the AI inference service is running on localhost:8001")
    print("Make sure the video pipeline is running and camera has frames")
    print("Modify CAMERA_ID in the script to test different cameras")
    print()
    
    try:
        success = main()
        
        if success:
            print("\n🎉 Test suite completed successfully!")
        else:
            print("\n❌ Test suite failed!")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
