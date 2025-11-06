"""
Advanced Detection service for Road Safety Violation Detector
Uses YOLOv8 with spatial reasoning for helmet and vehicle violations
Integrated from Capstone project for superior accuracy
"""

import sys
import os
import cv2
import numpy as np
import time
from typing import Dict, List, Tuple, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from configs.config import MODEL_PATH, CONFIDENCE_THRESHOLD
from road_safety_violation_detector.website.spatial_logic import (
    assign_riders_to_bike, 
    has_helmet_for_person, 
    count_riders_on_bike,
    bbox_center
)
from road_safety_violation_detector.website.plate_reader import PlateReader

# Class names mapping
CLASS_PERSON = "person"
CLASS_BIKE = "motorbike"
CLASS_HELMET = "helmet"
CLASS_PLATE = "license_plate"

BBox = Tuple[int, int, int, int]


class ViolationDetector:
    """Advanced violation detector with spatial reasoning"""
    
    def __init__(self):
        self.model = None
        self.confidence_threshold = CONFIDENCE_THRESHOLD
        self.plate_reader = PlateReader()
        self.load_model()
    
    def load_model(self):
        """Load YOLOv8 model with priority: Custom Indonesian > YOLOv8m > YOLOv8n"""
        try:
            from ultralytics import YOLO
            
            # Model priority order
            model_dir = os.path.dirname(MODEL_PATH)
            custom_model_path = os.path.join(model_dir, 'yolov8_custom_indonesian.pt')
            model_m_path = os.path.join(model_dir, 'yolov8m.pt')
            
            # 1. Try custom Indonesian traffic model first (BEST)
            if os.path.exists(custom_model_path):
                self.model = YOLO(custom_model_path)
                self.model_type = "custom_indonesian"
                print(f"✨ Loaded CUSTOM Indonesian model from {custom_model_path}")
                print(f"   Trained on 2,028 Indonesian traffic violation images")
                print(f"   Classes: Helm, Pengendara, PlatNomor, TanpaHelm")
            # 2. Try YOLOv8m (medium) for better accuracy
            elif os.path.exists(model_m_path):
                self.model = YOLO(model_m_path)
                self.model_type = "yolov8m"
                print(f"Loaded YOLOv8m (Medium) model from {model_m_path} - Better accuracy!")
            # 3. Fallback to YOLOv8n (nano)
            elif os.path.exists(MODEL_PATH):
                self.model = YOLO(MODEL_PATH)
                self.model_type = "yolov8n"
                print(f"Loaded YOLOv8n (Nano) model from {MODEL_PATH}")
            else:
                print(f"Model file not found at {MODEL_PATH}, {model_m_path}, or {custom_model_path}")
                self.model = None
                self.model_type = "none"
        except ImportError:
            print("ultralytics not available. Using fallback detection")
            self.model = None
            self.model_type = "none"
    
    def detect_violations(self, frame):
        """
        Detect violations using advanced spatial reasoning
        
        Args:
            frame (numpy.ndarray): Input image frame
            
        Returns:
            dict: Detection results with violations and metadata
        """
        if self.model is not None:
            return self._yolo_advanced_detection(frame)
        else:
            return self._fallback_detection(frame)
    
    def _yolo_advanced_detection(self, frame):
        """
        Advanced YOLOv8 detection with spatial reasoning for violations
        Based on Capstone's superior detection logic
        """
        try:
            # Run YOLO inference with optimized parameters
            results = self.model.predict(frame, imgsz=960, conf=0.25, iou=0.5, verbose=False)[0]
            
            # Organize detections by class
            bboxes: Dict[str, List[BBox]] = {
                CLASS_PERSON: [],
                CLASS_BIKE: [],
                CLASS_HELMET: [],
                CLASS_PLATE: []
            }
            scores: Dict[str, List[float]] = {
                CLASS_PERSON: [],
                CLASS_BIKE: [],
                CLASS_HELMET: [],
                CLASS_PLATE: []
            }
            
            names = results.names
            
            # Track direct violations from custom Indonesian model
            direct_violations = []
            
            # Extract bounding boxes by class
            for box in results.boxes:
                cls_id = int(box.cls[0])
                cls_name = names.get(cls_id, str(cls_id)).lower()
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                
                # Convert to bbox format
                bbox = self._to_bbox(xyxy)
                
                # Handle Indonesian custom model classes
                if self.model_type == "custom_indonesian":
                    # Indonesian class name mapping
                    if cls_name in ("pengendara",):  # Rider
                        bboxes[CLASS_PERSON].append(bbox)
                        scores[CLASS_PERSON].append(conf)
                    elif cls_name in ("helm",):  # Helmet
                        bboxes[CLASS_HELMET].append(bbox)
                        scores[CLASS_HELMET].append(conf)
                    elif cls_name in ("platnomor",):  # License Plate
                        bboxes[CLASS_PLATE].append(bbox)
                        scores[CLASS_PLATE].append(conf)
                    elif cls_name in ("tanpahelm",):  # Without Helmet - DIRECT VIOLATION!
                        # Treat as person without helmet
                        bboxes[CLASS_PERSON].append(bbox)
                        scores[CLASS_PERSON].append(conf)
                        # Record as direct violation
                        direct_violations.append({
                            "type": "helmet_violation",
                            "bbox": bbox,
                            "confidence": conf,
                            "detected_directly": True
                        })
                else:
                    # Standard COCO model class names
                    if cls_name in ("person",):
                        bboxes[CLASS_PERSON].append(bbox)
                        scores[CLASS_PERSON].append(conf)
                    elif cls_name in ("motorbike", "motorcycle", "bike"):
                        bboxes[CLASS_BIKE].append(bbox)
                        scores[CLASS_BIKE].append(conf)
                    elif cls_name in ("helmet",):
                        bboxes[CLASS_HELMET].append(bbox)
                        scores[CLASS_HELMET].append(conf)
                    elif cls_name in ("license_plate", "number_plate", "plate"):
                        bboxes[CLASS_PLATE].append(bbox)
                        scores[CLASS_PLATE].append(conf)
            
            # Extract lists
            persons = bboxes[CLASS_PERSON]
            bikes = bboxes[CLASS_BIKE]
            helmets = bboxes[CLASS_HELMET]
            plates = bboxes[CLASS_PLATE]
            
            # Detect violations using spatial reasoning
            violations = []
            
            # Add direct violations from custom Indonesian model
            if self.model_type == "custom_indonesian" and direct_violations:
                violations.extend(direct_violations)
                print(f"✨ Custom model detected {len(direct_violations)} direct violations (TanpaHelm)!")
            
            # Continue with spatial reasoning for additional violations
            for bike_bbox in bikes:
                # Assign riders to this bike using spatial logic
                riders = assign_riders_to_bike(bike_bbox, persons)
                rider_count = len(riders)
                
                # Check triple riding
                if rider_count >= 3:
                    violations.append({
                        "type": "triple_riding",
                        "bike_bbox": bike_bbox,
                        "riders": rider_count,
                        "confidence": 0.90
                    })
                
                # Check helmet violations for each rider (skip if already detected directly)
                if self.model_type != "custom_indonesian":  # Only do spatial check for non-custom models
                    for rider_bbox in riders:
                        if not has_helmet_for_person(rider_bbox, helmets):
                            violations.append({
                                "type": "helmet_violation",
                                "rider_bbox": rider_bbox,
                                "bike_bbox": bike_bbox,
                                "confidence": 0.85
                            })
            
            # Generate custom color-coded annotated image
            annotated = frame.copy()
            
            # Create violation lookup for detailed labeling
            violation_map = {}  # bbox -> list of violations
            for v in violations:
                if 'rider_bbox' in v:
                    if v['rider_bbox'] not in violation_map:
                        violation_map[v['rider_bbox']] = []
                    violation_map[v['rider_bbox']].append(v)
                if 'bike_bbox' in v:
                    if v['bike_bbox'] not in violation_map:
                        violation_map[v['bike_bbox']] = []
                    violation_map[v['bike_bbox']].append(v)
                if 'bbox' in v:  # For direct TanpaHelm detections
                    if v['bbox'] not in violation_map:
                        violation_map[v['bbox']] = []
                    violation_map[v['bbox']].append(v)
            
            # Draw bounding boxes with color coding and detailed labels
            # 1. Draw bikes (green if compliant, red if violation)
            for bike_bbox in bikes:
                is_violation = bike_bbox in violation_map
                color = (0, 0, 255) if is_violation else (0, 255, 0)  # Red or Green
                x1, y1, x2, y2 = bike_bbox
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
                
                if is_violation:
                    # Show violation-specific labels with confidence
                    violations_here = violation_map[bike_bbox]
                    y_label = y1 - 10
                    for v in violations_here:
                        vtype = v['type'].replace('_', ' ').title()
                        conf = v.get('confidence', 0.0) * 100
                        label = f"{vtype} {conf:.0f}%"
                        cv2.putText(annotated, label, (x1, y_label), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        y_label -= 20
                else:
                    cv2.putText(annotated, 'Compliant Vehicle', (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # 2. Draw persons/riders (red if violation, green if compliant)
            for person_bbox in persons:
                is_violation = person_bbox in violation_map
                color = (0, 0, 255) if is_violation else (0, 255, 0)  # Red or Green
                x1, y1, x2, y2 = person_bbox
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
                
                if is_violation:
                    # Show violation-specific labels with confidence
                    violations_here = violation_map[person_bbox]
                    y_label = y1 - 10
                    for v in violations_here:
                        vtype = v['type'].replace('_', ' ').title()
                        conf = v.get('confidence', 0.0) * 100
                        label = f"{vtype} {conf:.0f}%"
                        cv2.putText(annotated, label, (x1, y_label), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        y_label -= 20
                else:
                    cv2.putText(annotated, 'Compliant Rider', (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # 3. Draw helmets (blue)
            for helmet_bbox in helmets:
                x1, y1, x2, y2 = helmet_bbox
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 0, 0), 3)  # Blue
                cv2.putText(annotated, 'Helmet Detected', (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # 4. Draw license plates (orange) with OCR extraction
            plate_numbers = []
            for plate_bbox in plates:
                x1, y1, x2, y2 = plate_bbox
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 165, 255), 3)  # Orange
                
                # Extract plate region and run OCR
                plate_region = frame[y1:y2, x1:x2]
                if plate_region.size > 0:
                    plate_text = self.plate_reader.read_plate(plate_region)
                    if plate_text and plate_text != 'UNKNOWN':
                        plate_numbers.append({
                            'number': plate_text,
                            'bbox': plate_bbox,
                            'confidence': 0.85
                        })
                        label = f'Plate: {plate_text}'
                    else:
                        label = 'License Plate'
                else:
                    label = 'License Plate'
                
                cv2.putText(annotated, label, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            
            # Add violation summary panel at top
            y_offset = 30
            if violations:
                # Semi-transparent background for violation panel
                overlay = annotated.copy()
                cv2.rectangle(overlay, (10, 10), (400, 30 + len(violations) * 35), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, annotated, 0.4, 0, annotated)
                
                cv2.putText(annotated, f"VIOLATIONS DETECTED: {len(violations)}", (20, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                y_offset = 60
                for v in violations:
                    vtype = v['type'].replace('_', ' ').title()
                    conf = v.get('confidence', 0.0) * 100
                    text = f"{vtype} ({conf:.0f}%)"
                    cv2.putText(annotated, text, (20, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    y_offset += 30
            else:
                # No violations message
                cv2.putText(annotated, "No Violations Detected", (20, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Prepare metadata
            metadata = {
                "violations": violations,
                "counts": {
                    "persons": len(persons),
                    "bikes": len(bikes),
                    "helmets": len(helmets),
                    "plates": len(plates)
                },
                "bboxes": bboxes,
                "scores": scores,
                "plate_numbers": plate_numbers,
                "is_vehicle_image": len(bikes) > 0 or len(persons) > 0,
                "annotated_image": annotated,
                "raw_result": results
            }
            
            return metadata
            
        except Exception as e:
            print(f"Error in YOLO detection: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_detection(frame)
    
    def _to_bbox(self, xyxy) -> BBox:
        """Convert YOLO xyxy format to bbox tuple"""
        x1, y1, x2, y2 = map(int, xyxy)
        return (x1, y1, x2, y2)
    
    def _fallback_detection(self, frame):
        """Simple fallback detection when YOLO unavailable"""
        violations = []
        
        # Basic vehicle detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        vehicle_count = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if 2000 < area < 50000:
                vehicle_count += 1
                if vehicle_count <= 2:  # Limit fallback detections
                    violations.append({
                        "type": "helmet_violation",
                        "confidence": 0.65
                    })
        
        return {
            "violations": violations,
            "counts": {"persons": 0, "bikes": vehicle_count, "helmets": 0, "plates": 0},
            "bboxes": {CLASS_PERSON: [], CLASS_BIKE: [], CLASS_HELMET: [], CLASS_PLATE: []},
            "scores": {CLASS_PERSON: [], CLASS_BIKE: [], CLASS_HELMET: [], CLASS_PLATE: []},
            "plate_numbers": [],
            "is_vehicle_image": vehicle_count > 0,
            "annotated_image": frame.copy(),
            "raw_result": None
        }
    
    def extract_plate_region(self, frame, bbox):
        """Extract license plate region from frame"""
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        margin = 10
        h, w = frame.shape[:2]
        x1 = max(0, x1 - margin)
        y1 = max(0, y1 - margin)
        x2 = min(w, x2 + margin)
        y2 = min(h, y2 + margin)
        return frame[y1:y2, x1:x2]


def run_detection(image_path):
    """Run detection on an image"""
    detector = ViolationDetector()
    
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return {}
    
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"Could not read image: {image_path}")
        return {}
    
    results = detector.detect_violations(frame)
    
    print(f"Detected {len(results.get('violations', []))} violations")
    for i, violation in enumerate(results.get('violations', [])):
        print(f"  {i+1}. Type: {violation['type']}, Confidence: {violation.get('confidence', 0):.2f}")
    
    return results
