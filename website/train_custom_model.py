"""
Custom YOLOv8 Training Script for Indonesian Traffic Violations
Trains on deteksi_pelanggran dataset from Roboflow
"""

import os
import sys
from ultralytics import YOLO
from datetime import datetime

def train_custom_model():
    """Train YOLOv8 on Indonesian traffic violation dataset"""
    
    print("=" * 80)
    print("🚀 CUSTOM YOLOV8 TRAINING FOR INDONESIAN TRAFFIC VIOLATIONS")
    print("=" * 80)
    
    # Configuration
    data_yaml = "training_data/data.yaml"
    base_model = "models/yolov8m.pt"  # Use YOLOv8m as starting point
    output_dir = "models/custom"
    
    # Training parameters
    epochs = 50  # Adjust based on time available (can increase for better accuracy)
    imgsz = 640  # Image size for training
    batch = 16   # Batch size (adjust based on memory)
    patience = 10  # Early stopping patience
    
    # Check if data.yaml exists
    if not os.path.exists(data_yaml):
        print(f"❌ Error: {data_yaml} not found!")
        return
    
    # Check if base model exists
    if not os.path.exists(base_model):
        print(f"⚠️ Warning: {base_model} not found. Downloading YOLOv8m...")
        model = YOLO("yolov8m.pt")
    else:
        print(f"✅ Loading base model: {base_model}")
        model = YOLO(base_model)
    
    print(f"\n📊 Training Configuration:")
    print(f"   Dataset: Indonesian Traffic Violations")
    print(f"   Base Model: YOLOv8m (transfer learning)")
    print(f"   Classes: 4 (Helm, Pengendara, PlatNomor, TanpaHelm)")
    print(f"   Training Images: 2,028")
    print(f"   Validation Images: 195")
    print(f"   Epochs: {epochs}")
    print(f"   Image Size: {imgsz}x{imgsz}")
    print(f"   Batch Size: {batch}")
    print(f"   Early Stopping: {patience} epochs")
    
    print(f"\n🎯 Starting Training...")
    print("   This will take 30-60 minutes depending on hardware")
    print("   Progress will be shown below:\n")
    
    try:
        # Start training
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            patience=patience,
            save=True,
            project=output_dir,
            name=f"traffic_violations_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            verbose=True,
            plots=True,  # Generate training plots
            device='cpu',  # Use CPU (change to 'cuda' if GPU available)
        )
        
        print("\n" + "=" * 80)
        print("✅ TRAINING COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
        # Print results
        print(f"\n📊 Training Results:")
        print(f"   Best Model Saved: {results.save_dir}/weights/best.pt")
        print(f"   Last Model Saved: {results.save_dir}/weights/last.pt")
        print(f"   Training Plots: {results.save_dir}/")
        
        # Copy best model to main models directory
        best_model_path = f"{results.save_dir}/weights/best.pt"
        custom_model_path = "models/yolov8_custom_indonesian.pt"
        
        if os.path.exists(best_model_path):
            import shutil
            shutil.copy(best_model_path, custom_model_path)
            print(f"\n✅ Custom model copied to: {custom_model_path}")
            print(f"   This model is now ready to use in your detection system!")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Update detection system to use custom model")
        print(f"   2. Test on sample images")
        print(f"   3. Compare performance with YOLOv8m")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Training failed with error:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"\n📍 Working directory: {os.getcwd()}\n")
    
    # Change to road_safety_violation_detector directory if needed
    if not os.path.exists("training_data"):
        if os.path.exists("road_safety_violation_detector/training_data"):
            os.chdir("road_safety_violation_detector")
            print(f"✅ Changed to: {os.getcwd()}\n")
    
    success = train_custom_model()
    
    if success:
        print("\n🎉 Custom model training completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Training failed. Check errors above.")
        sys.exit(1)
