"""
Check YOLOv8 Training Progress
Monitors training logs and displays current status
"""

import os
import glob
from pathlib import Path

def check_training_progress():
    """Check the progress of YOLOv8 training"""
    
    print("=" * 80)
    print("📊 CHECKING TRAINING PROGRESS")
    print("=" * 80)
    
    # Find training directories
    custom_dir = "models/custom"
    
    if not os.path.exists(custom_dir):
        print(f"\n❌ Training directory not found: {custom_dir}")
        print(f"   Training has not started yet.")
        return
    
    # Find all training runs
    training_runs = glob.glob(f"{custom_dir}/traffic_violations_*")
    
    if not training_runs:
        print(f"\n❌ No training runs found in {custom_dir}")
        return
    
    # Get the most recent training run
    latest_run = max(training_runs, key=os.path.getctime)
    
    print(f"\n📁 Latest training run: {os.path.basename(latest_run)}")
    
    # Check for weights
    weights_dir = os.path.join(latest_run, "weights")
    if os.path.exists(weights_dir):
        print(f"\n🏋️  Model weights:")
        for weight_file in ["best.pt", "last.pt"]:
            weight_path = os.path.join(weights_dir, weight_file)
            if os.path.exists(weight_path):
                size_mb = os.path.getsize(weight_path) / (1024 * 1024)
                print(f"   ✅ {weight_file}: {size_mb:.1f} MB")
            else:
                print(f"   ⏳ {weight_file}: Not yet created")
    
    # Check for results
    results_file = os.path.join(latest_run, "results.csv")
    if os.path.exists(results_file):
        print(f"\n📈 Training results file found")
        # Read last line to get latest epoch
        with open(results_file, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:
                last_line = lines[-1].strip()
                print(f"   Latest epoch data: {last_line[:100]}...")
    else:
        print(f"\n⏳ Results file not yet created - training in early stages")
    
    # Check for plots
    plots = glob.glob(f"{latest_run}/*.png")
    if plots:
        print(f"\n📊 Training plots generated: {len(plots)} images")
        for plot in plots[:5]:
            print(f"   - {os.path.basename(plot)}")
        if len(plots) > 5:
            print(f"   ... and {len(plots)-5} more")
    
    # Check training log
    if os.path.exists("training_log.txt"):
        print(f"\n📝 Training log file: training_log.txt")
        print(f"   Use: tail -f training_log.txt  to monitor progress")
    
    print(f"\n{'='*80}")
    print(f"💡 Training Status:")
    
    if os.path.exists(os.path.join(weights_dir, "best.pt")):
        print(f"   ✅ Training completed or in progress (model checkpoint saved)")
        print(f"   📍 Best model: {os.path.join(weights_dir, 'best.pt')}")
    else:
        print(f"   ⏳ Training in progress (no checkpoint yet)")
        print(f"   Please wait for training to complete")
    
    print(f"{'='*80}\n")

if __name__ == "__main__":
    if os.path.exists("training_data"):
        check_training_progress()
    else:
        os.chdir("road_safety_violation_detector")
        check_training_progress()
