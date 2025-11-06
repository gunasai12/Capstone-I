"""
Demo data seeding script for Road Safety Violation Detector
Creates sample violations for demonstration purposes
"""

import sys
import os
import cv2
import numpy as np
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db.models import DatabaseManager
from configs.config import DATABASE_PATH, VIOLATIONS_STORAGE
from road_safety_violation_detector.website.rules import compute_fine
from road_safety_violation_detector.website.pdf_generator import build_pdf

def create_sample_image(vehicle_no, violation_type):
    """Create a sample violation image for demo purposes"""
    # Create a simple demo image
    img = np.ones((300, 400, 3), dtype=np.uint8) * 128  # Gray background
    
    # Add some text to simulate a violation scene
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Title
    cv2.putText(img, "VIOLATION DETECTED", (50, 50), font, 0.7, (0, 0, 255), 2)
    
    # Vehicle number
    cv2.putText(img, f"Vehicle: {vehicle_no}", (50, 100), font, 0.6, (255, 255, 255), 2)
    
    # Violation type
    cv2.putText(img, f"Type: {violation_type}", (50, 130), font, 0.5, (255, 255, 255), 1)
    
    # Add some shapes to simulate a vehicle/road scene
    cv2.rectangle(img, (100, 150), (300, 250), (100, 100, 100), -1)  # Vehicle shape
    cv2.rectangle(img, (120, 170), (140, 200), (255, 255, 0), -1)    # License plate
    
    if violation_type == 'NO_HELMET':
        cv2.circle(img, (200, 160), 15, (255, 0, 0), -1)  # Head without helmet
        cv2.putText(img, "NO HELMET", (160, 280), font, 0.5, (0, 0, 255), 2)
    elif violation_type == 'TRIPLE_RIDING':
        cv2.circle(img, (180, 160), 10, (255, 255, 255), -1)  # Person 1
        cv2.circle(img, (200, 160), 10, (255, 255, 255), -1)  # Person 2
        cv2.circle(img, (220, 160), 10, (255, 255, 255), -1)  # Person 3
        cv2.putText(img, "3 RIDERS", (160, 280), font, 0.5, (0, 0, 255), 2)
    
    return img

def seed_demo_violations():
    """Create demo violation data"""
    print("Seeding demo violation data...")
    
    # Initialize database
    db = DatabaseManager(DATABASE_PATH)
    
    # Ensure storage directory exists
    os.makedirs(VIOLATIONS_STORAGE, exist_ok=True)
    
    # Demo violation data with locations
    demo_violations = [
        {
            'vehicle_no': 'MH01AB1234',
            'violation_type': 'NO_HELMET',
            'hours_ago': 2,
            'location_text': 'Mumbai-Pune Highway, Near Lonavala Toll Plaza',
            'latitude': 18.7533,
            'longitude': 73.4094
        },
        {
            'vehicle_no': 'KA05CD5678',
            'violation_type': 'TRIPLE_RIDING',
            'hours_ago': 5,
            'location_text': 'Outer Ring Road, Marathahalli Junction, Bangalore',
            'latitude': 12.9593,
            'longitude': 77.7069
        },
        {
            'vehicle_no': 'MH01AB1234',  # Repeat offender
            'violation_type': 'NO_HELMET',
            'hours_ago': 8,
            'location_text': 'Senapati Bapat Road, Pune',
            'latitude': 18.5193,
            'longitude': 73.8277
        },
        {
            'vehicle_no': 'TN07EF9012',
            'violation_type': 'TRIPLE_RIDING',
            'hours_ago': 12,
            'location_text': 'Chennai-Bangalore Highway, Electronic City',
            'latitude': 12.8406,
            'longitude': 77.6595
        },
        {
            'vehicle_no': 'DL03GH3456',
            'violation_type': 'NO_HELMET',
            'hours_ago': 24,
            'location_text': 'Connaught Place, Central Delhi',
            'latitude': 28.6315,
            'longitude': 77.2167
        }
    ]
    
    created_violations = []
    
    for i, violation_data in enumerate(demo_violations):
        vehicle_no = violation_data['vehicle_no']
        violation_type = violation_data['violation_type']
        hours_ago = violation_data['hours_ago']
        location_text = violation_data.get('location_text')
        latitude = violation_data.get('latitude')
        longitude = violation_data.get('longitude')
        
        print(f"Creating violation {i+1}: {vehicle_no} - {violation_type} at {location_text}")
        
        # Create sample image
        sample_img = create_sample_image(vehicle_no, violation_type)
        
        # Save image
        img_filename = f"demo_violation_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        img_path = os.path.join(VIOLATIONS_STORAGE, img_filename)
        cv2.imwrite(img_path, sample_img)
        
        # Compute fine
        fine_amount = compute_fine(vehicle_no, violation_type, db)
        
        # Generate description
        descriptions = {
            'NO_HELMET': f"Vehicle {vehicle_no} observed riding without mandatory helmet at {location_text}. Driver failed to comply with safety regulations requiring protective headgear for two-wheeler operators.",
            'TRIPLE_RIDING': f"Vehicle {vehicle_no} found carrying excessive passengers exceeding the legal limit at {location_text}. Three persons observed on a two-wheeler designed for maximum two occupants."
        }
        
        description = descriptions.get(violation_type, f"Traffic violation detected for {vehicle_no} at {location_text}")
        
        # Insert violation into database
        violation_id = db.insert_violation(
            vehicle_no=vehicle_no,
            violation_type=violation_type,
            fine_amount=fine_amount,
            image_path=img_path,
            description=description,
            location_text=location_text,
            latitude=latitude,
            longitude=longitude
        )
        
        # Update timestamp to simulate violations at different times
        violation_time = datetime.now() - timedelta(hours=hours_ago)
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE violations SET timestamp = ? WHERE id = ?',
            (violation_time.strftime('%Y-%m-%d %H:%M:%S'), violation_id)
        )
        conn.commit()
        conn.close()
        
        # Generate PDF
        pdf_path = build_pdf(violation_id)
        
        created_violations.append({
            'id': violation_id,
            'vehicle_no': vehicle_no,
            'violation_type': violation_type,
            'fine_amount': fine_amount,
            'image_path': img_path,
            'pdf_path': pdf_path
        })
        
        print(f"  Created violation ID: {violation_id}, Fine: ₹{fine_amount}")
        if pdf_path:
            print(f"  Generated PDF: {pdf_path}")
    
    print(f"\nDemo data seeding complete! Created {len(created_violations)} violations.")
    
    # Print summary
    print("\nSummary:")
    for violation in created_violations:
        print(f"  {violation['vehicle_no']}: {violation['violation_type']} - ₹{violation['fine_amount']}")
    
    return created_violations

def main():
    """Main function for command line usage"""
    violations = seed_demo_violations()
    print(f"\nYou can now search for these vehicles in the web interface:")
    unique_vehicles = set(v['vehicle_no'] for v in violations)
    for vehicle in sorted(unique_vehicles):
        print(f"  - {vehicle}")

if __name__ == "__main__":
    main()