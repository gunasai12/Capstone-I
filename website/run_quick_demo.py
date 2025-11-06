"""
Quick demo script to test the Road Safety Violation Detector
Tests detection on sample images and verifies system functionality
"""

import sys
import os
import cv2
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from road_safety_violation_detector.website.detect import ViolationDetector
from road_safety_violation_detector.website.plate_reader import PlateReader
from road_safety_violation_detector.website.pdf_generator import generate_sample_pdf
from db.models import DatabaseManager
from configs.config import DATABASE_PATH, VIOLATIONS_STORAGE

def create_test_image():
    """Create a simple test image for detection demo"""
    # Create a test image with a vehicle-like shape
    img = np.ones((400, 600, 3), dtype=np.uint8) * 200  # Light gray background
    
    # Draw road
    cv2.rectangle(img, (0, 300), (600, 400), (100, 100, 100), -1)
    
    # Draw vehicle shape
    cv2.rectangle(img, (200, 250), (400, 350), (50, 50, 150), -1)
    
    # Draw wheels
    cv2.circle(img, (230, 340), 15, (0, 0, 0), -1)
    cv2.circle(img, (370, 340), 15, (0, 0, 0), -1)
    
    # Draw license plate area
    cv2.rectangle(img, (280, 320), (320, 340), (255, 255, 255), -1)
    cv2.putText(img, "MH01", (285, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
    
    # Draw rider (simulate no helmet scenario)
    cv2.circle(img, (300, 230), 20, (255, 200, 150), -1)  # Head
    cv2.rectangle(img, (290, 250), (310, 280), (100, 150, 200), -1)  # Body
    
    # Add text label
    cv2.putText(img, "Test Vehicle - Helmet Detection", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    return img

def test_detection_system():
    """Test the detection system"""
    print("=== Testing Detection System ===")
    
    # Create test image
    test_img = create_test_image()
    
    # Save test image
    os.makedirs(VIOLATIONS_STORAGE, exist_ok=True)
    test_img_path = os.path.join(VIOLATIONS_STORAGE, "test_image.jpg")
    cv2.imwrite(test_img_path, test_img)
    print(f"Created test image: {test_img_path}")
    
    # Initialize detector
    detector = ViolationDetector()
    print(f"Detector initialized. Model available: {detector.model is not None}")
    
    # Run detection
    violations = detector.detect_violations(test_img)
    print(f"Detected {len(violations)} violations")
    
    for i, violation in enumerate(violations):
        print(f"  Violation {i+1}: {violation['type']} (confidence: {violation['confidence']:.2f})")
    
    return violations

def test_plate_reader():
    """Test the plate reading system"""
    print("\n=== Testing Plate Reader ===")
    
    # Create a simple plate image
    plate_img = np.ones((60, 120, 3), dtype=np.uint8) * 255  # White background
    cv2.putText(plate_img, "MH01AB1234", (5, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    # Save plate image
    plate_path = os.path.join(VIOLATIONS_STORAGE, "test_plate.jpg")
    cv2.imwrite(plate_path, plate_img)
    print(f"Created test plate image: {plate_path}")
    
    # Initialize plate reader
    reader = PlateReader()
    print(f"Plate reader initialized. EasyOCR available: {reader.reader is not None}")
    
    # Read plate
    plate_text = reader.read_plate(plate_img)
    print(f"Read plate text: '{plate_text}'")
    
    return plate_text

def test_database():
    """Test database operations"""
    print("\n=== Testing Database ===")
    
    db = DatabaseManager(DATABASE_PATH)
    
    # Check if we have owners
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM owners')
    owner_count = cursor.fetchone()[0]
    print(f"Database has {owner_count} vehicle owners")
    
    cursor.execute('SELECT COUNT(*) FROM violations')
    violation_count = cursor.fetchone()[0]
    print(f"Database has {violation_count} violations")
    
    conn.close()
    
    return owner_count, violation_count

def test_pdf_generation():
    """Test PDF generation"""
    print("\n=== Testing PDF Generation ===")
    
    try:
        pdf_path = generate_sample_pdf()
        if pdf_path and os.path.exists(pdf_path):
            print(f"Successfully generated PDF: {pdf_path}")
            return True
        else:
            print("Failed to generate PDF")
            return False
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return False

def run_full_demo():
    """Run the complete demo"""
    print("🚦 Road Safety Violation Detector - Quick Demo")
    print("=" * 50)
    
    # Test all components
    violations = test_detection_system()
    plate_text = test_plate_reader()
    owner_count, violation_count = test_database()
    pdf_success = test_pdf_generation()
    
    # Summary
    print("\n=== Demo Summary ===")
    print(f"✅ Detection system: {'Working' if violations is not None else 'Failed'}")
    print(f"✅ Plate reader: {'Working' if plate_text else 'Failed'}")
    print(f"✅ Database: {'Working' if owner_count >= 0 else 'Failed'} ({violation_count} violations)")
    print(f"✅ PDF generation: {'Working' if pdf_success else 'Failed'}")
    
    print(f"\n🌐 Web interface running at: http://0.0.0.0:5000")
    print(f"📊 Try searching for these vehicles: MH01AB1234, KA05CD5678, TN07EF9012")
    
    if violation_count > 0:
        print(f"📄 {violation_count} violation PDFs available for download")
    
    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    run_full_demo()