"""
Test Custom YOLOv8 Model on Sample Images
Compare custom Indonesian model vs standard YOLOv8m
"""

import os
import cv2
from ultralytics import YOLO

def test_custom_model():
    """Test the custom-trained model on sample images"""
    
    print("=" * 80)
    print("🧪 TESTING CUSTOM INDONESIAN TRAFFIC VIOLATION MODEL")
    print("=" * 80)
    
    # Model paths
    custom_model_path = "models/yolov8_custom_indonesian.pt"
    standard_model_path = "models/yolov8m.pt"
    
    # Test images
    test_images = [
        "media/uploads/test_motorcycle_clear.jpg",
        "media/uploads/test_traffic.png"
    ]
    
    # Check if custom model exists
    if not os.path.exists(custom_model_path):
        print(f"❌ Custom model not found: {custom_model_path}")
        print(f"   Training may still be in progress or failed.")
        print(f"   Check: models/custom/traffic_violations_*/weights/best.pt")
        return False
    
    print(f"\n✅ Loading models for comparison...")
    custom_model = YOLO(custom_model_path)
    standard_model = YOLO(standard_model_path)
    
    print(f"\n📊 Model Comparison:\n")
    
    for img_path in test_images:
        if not os.path.exists(img_path):
            print(f"⚠️ Skipping {img_path} - file not found")
            continue
            
        print(f"\n{'='*80}")
        print(f"📸 Testing: {os.path.basename(img_path)}")
        print(f"{'='*80}")
        
        img = cv2.imread(img_path)
        
        # Run standard model
        print(f"\n🔹 Standard YOLOv8m (COCO trained):")
        std_results = standard_model.predict(img, conf=0.25, verbose=False)[0]
        std_detections = {}
        for box in std_results.boxes:
            cls_name = std_results.names[int(box.cls[0])]
            std_detections[cls_name] = std_detections.get(cls_name, 0) + 1
        
        for cls, count in std_detections.items():
            print(f"   {cls}: {count}")
        
        # Run custom model
        print(f"\n🔸 Custom Indonesian Model:")
        custom_results = custom_model.predict(img, conf=0.25, verbose=False)[0]
        custom_detections = {}
        for box in custom_results.boxes:
            cls_name = custom_results.names[int(box.cls[0])]
            conf = float(box.conf[0])
            custom_detections[cls_name] = custom_detections.get(cls_name, [])
            custom_detections[cls_name].append(conf)
        
        for cls, confs in custom_detections.items():
            avg_conf = sum(confs) / len(confs)
            print(f"   {cls}: {len(confs)} (avg confidence: {avg_conf:.1%})")
        
        # Highlight violations
        if 'TanpaHelm' in custom_detections:
            print(f"\n⚠️  VIOLATION DETECTED: {len(custom_detections['TanpaHelm'])} riders without helmet!")
        
        print(f"\n{'='*80}\n")
    
    print(f"\n✅ Testing complete!")
    print(f"\n📊 Custom Model Classes:")
    print(f"   0: Helm (Helmet)")
    print(f"   1: Pengendara (Rider)")
    print(f"   2: PlatNomor (License Plate)")
    print(f"   3: TanpaHelm (Without Helmet - VIOLATION)")
    
    return True

if __name__ == "__main__":
    if os.path.exists("training_data"):
        test_custom_model()
    else:
        os.chdir("road_safety_violation_detector")
        test_custom_model()
