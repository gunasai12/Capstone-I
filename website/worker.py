"""
Worker script for processing videos and detecting violations
Processes video frames, detects violations, reads plates, and generates reports
"""

import sys
import os
import cv2
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from configs.config import SAMPLE_VIDEO_PATH, FRAME_SKIP, VIOLATIONS_STORAGE
from road_safety_violation_detector.website.detect import ViolationDetector
from road_safety_violation_detector.website.plate_reader import PlateReader
from road_safety_violation_detector.website.rules import compute_fine
from road_safety_violation_detector.website.pdf_generator import build_pdf
from db.models import DatabaseManager

class ViolationWorker:
    """Main worker class for processing videos and detecting violations"""
    
    def __init__(self):
        self.detector = ViolationDetector()
        self.plate_reader = PlateReader()
        self.db = DatabaseManager(DATABASE_PATH)
        
        # Ensure storage directories exist
        os.makedirs(VIOLATIONS_STORAGE, exist_ok=True)
    
    def process_video(self, video_path):
        """
        Process a video file for violations
        
        Args:
            video_path (str): Path to video file
            
        Returns:
            list: List of processed violations
        """
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return []
        
        violations_found = []
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Could not open video: {video_path}")
            return []
        
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Processing video: {video_path}")
        print(f"Total frames: {total_frames}, FPS: {fps}")
        print(f"Processing every {FRAME_SKIP} frames...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Process every Nth frame
            if frame_count % FRAME_SKIP == 0:
                timestamp = frame_count / fps
                print(f"Processing frame {frame_count} (time: {timestamp:.1f}s)")
                
                # Detect violations in this frame
                detections = self.detector.detect_violations(frame)
                
                for detection in detections:
                    violation = self.process_violation(frame, detection, frame_count, timestamp)
                    if violation:
                        violations_found.append(violation)
        
        cap.release()
        
        print(f"Video processing complete. Found {len(violations_found)} violations.")
        return violations_found
    
    def process_violation(self, frame, detection, frame_number, timestamp):
        """
        Process a single violation detection
        
        Args:
            frame (numpy.ndarray): Video frame
            detection (dict): Detection results
            frame_number (int): Frame number
            timestamp (float): Timestamp in video
            
        Returns:
            dict: Processed violation data
        """
        try:
            violation_type = detection['type']
            bbox = detection['bbox']
            confidence = detection['confidence']
            
            print(f"  Processing {violation_type} violation (confidence: {confidence:.2f})")
            
            # Extract plate region
            plate_region = self.detector.extract_plate_region(frame, bbox)
            
            # Read number plate
            vehicle_no = self.plate_reader.read_plate(plate_region)
            
            if vehicle_no == 'UNKNOWN':
                print(f"    Could not read plate, skipping violation")
                return None
            
            print(f"    Detected vehicle: {vehicle_no}")
            
            # Compute fine
            fine_amount = compute_fine(vehicle_no, violation_type, self.db)
            
            # Save violation snapshot
            snapshot_filename = f"violation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{frame_number}.jpg"
            snapshot_path = os.path.join(VIOLATIONS_STORAGE, snapshot_filename)
            
            # Crop and save the violation area
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            violation_crop = frame[y1:y2, x1:x2]
            cv2.imwrite(snapshot_path, violation_crop)
            
            # Generate description
            description = self.generate_description(violation_type, vehicle_no, timestamp)
            
            # Insert violation into database
            violation_id = self.db.insert_violation(
                vehicle_no=vehicle_no,
                violation_type=violation_type,
                fine_amount=fine_amount,
                image_path=snapshot_path,
                description=description
            )
            
            print(f"    Violation logged with ID: {violation_id}")
            
            # Generate PDF e-challan
            pdf_path = build_pdf(violation_id)
            if pdf_path:
                print(f"    E-challan generated: {pdf_path}")
            
            return {
                'id': violation_id,
                'vehicle_no': vehicle_no,
                'violation_type': violation_type,
                'fine_amount': fine_amount,
                'snapshot_path': snapshot_path,
                'pdf_path': pdf_path,
                'timestamp': timestamp,
                'confidence': confidence
            }
            
        except Exception as e:
            print(f"Error processing violation: {e}")
            return None
    
    def generate_description(self, violation_type, vehicle_no, timestamp):
        """
        Generate description for violation
        
        Args:
            violation_type (str): Type of violation
            timestamp (float): Timestamp in video
            
        Returns:
            str: Generated description
        """
        # Check if OpenAI integration is available
        try:
            from road_safety_violation_detector.website.gpt_report import generate_description
            return generate_description({
                'violation_type': violation_type,
                'vehicle_no': vehicle_no,
                'timestamp': timestamp
            })
        except ImportError:
            # Use template description
            time_str = f"{int(timestamp//60):02d}:{int(timestamp%60):02d}"
            
            if violation_type == 'NO_HELMET':
                return f"Vehicle {vehicle_no} observed riding without helmet at {time_str}. This is a violation of traffic safety regulations requiring protective headgear."
            elif violation_type == 'TRIPLE_RIDING':
                return f"Vehicle {vehicle_no} observed with more than two riders at {time_str}. This exceeds the legal passenger limit for two-wheeler vehicles."
            else:
                return f"Traffic violation detected for vehicle {vehicle_no} at {time_str}."
    
    def process_sample_video(self):
        """Process the sample video"""
        return self.process_video(SAMPLE_VIDEO_PATH)

def main():
    """Main function for command line usage"""
    worker = ViolationWorker()
    
    # Check if sample video exists
    if os.path.exists(SAMPLE_VIDEO_PATH):
        print("Processing sample video...")
        violations = worker.process_sample_video()
        print(f"Processing complete. {len(violations)} violations detected.")
    else:
        print(f"Sample video not found at: {SAMPLE_VIDEO_PATH}")
        print("Please add a sample video or specify a video path")

if __name__ == "__main__":
    main()