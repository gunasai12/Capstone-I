"""
Advanced AI Detection wrapper for web app integration
Provides complete detection metadata including annotated images
"""

import cv2
import os
import json
import time
from .detect import ViolationDetector
from road_safety_violation_detector.website.paddle_ocr_reader import PaddleOCRReader, crop_from_bbox


def detect_violations(image_path, save_annotations=True):
    """
    Detect violations in an image with full metadata
    
    Args:
        image_path (str): Path to the image file
        save_annotations (bool): Whether to save annotated image
        
    Returns:
        dict: Complete detection results with violations, metadata, and annotated image
    """
    # Read image
    frame = cv2.imread(image_path)
    if frame is None:
        return {
            'violations': [],
            'is_vehicle_image': False,
            'error': 'Could not read image'
        }
    
    # Initialize detector
    detector = ViolationDetector()
    
    # Detect violations with advanced spatial reasoning
    detection_result = detector.detect_violations(frame)
    
    # Extract violations and metadata
    violations = detection_result.get('violations', [])
    counts = detection_result.get('counts', {})
    bboxes = detection_result.get('bboxes', {})
    is_vehicle_image = detection_result.get('is_vehicle_image', True)
    annotated_image = detection_result.get('annotated_image', frame.copy())
    
    # License plate OCR
    plate_text = 'UNKNOWN'
    plate_conf = 0.0
    plates = bboxes.get('license_plate', [])
    
    if plates:
        # Get largest plate
        areas = [(i, (b[2]-b[0])*(b[3]-b[1])) for i, b in enumerate(plates)]
        if areas:
            idx = max(areas, key=lambda t: t[1])[0]
            plate_bbox = plates[idx]
            plate_crop = crop_from_bbox(frame, plate_bbox)
            
            # Use PaddleOCR
            ocr_reader = PaddleOCRReader()
            plate_text, plate_conf = ocr_reader.read_plate(plate_crop)
    
    # Format violations for web app
    formatted_violations = []
    for violation in violations:
        if isinstance(violation, dict) and 'type' in violation:
            vtype = violation['type']
            confidence = violation.get('confidence', 0.8)
            
            # Normalize type names
            if vtype in ['NO_HELMET', 'no_helmet']:
                vtype = 'helmet_violation'
            elif vtype in ['TRIPLE_RIDING']:
                vtype = 'triple_riding'
            
            formatted_violations.append({
                'type': vtype,
                'confidence': confidence,
                'description': f"{vtype.replace('_', ' ').title()} detected with {confidence:.1%} confidence",
                'metadata': {
                    'bike_bbox': violation.get('bike_bbox'),
                    'rider_bbox': violation.get('rider_bbox'),
                    'riders': violation.get('riders')
                }
            })
    
    # Calculate aggregate detection confidence from all violations
    detection_confidence = None
    if formatted_violations:
        confidences = [v.get('confidence', 0.0) for v in formatted_violations]
        detection_confidence = sum(confidences) / len(confidences) if confidences else None
    
    # Prepare complete result
    result = {
        'violations': formatted_violations,
        'is_vehicle_image': is_vehicle_image,
        'license_plate': {
            'text': plate_text,
            'confidence': plate_conf
        },
        'counts': counts,
        'annotated_image': annotated_image,
        'timestamp': time.strftime("%Y%m%d_%H%M%S"),
        'detection_confidence': detection_confidence
    }
    
    return result


def save_detection_evidence(detection_result, image_path, output_dir):
    """
    Save detection evidence (annotated image + JSON metadata)
    
    Args:
        detection_result: Detection result from detect_violations()
        image_path: Original image path
        output_dir: Directory to save evidence
        
    Returns:
        dict: Paths to saved files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = detection_result.get('timestamp', time.strftime("%Y%m%d_%H%M%S"))
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    
    # Save annotated image
    annotated_path = os.path.join(output_dir, f"{base_name}_annotated_{timestamp}.jpg")
    annotated_image = detection_result.get('annotated_image')
    if annotated_image is not None:
        cv2.imwrite(annotated_path, annotated_image)
    
    # Save JSON metadata
    json_path = os.path.join(output_dir, f"{base_name}_evidence_{timestamp}.json")
    metadata = {
        'source_image': os.path.basename(image_path),
        'timestamp': timestamp,
        'violations': detection_result.get('violations', []),
        'license_plate': detection_result.get('license_plate', {}),
        'counts': detection_result.get('counts', {}),
        'is_vehicle_image': detection_result.get('is_vehicle_image', False),
        'detection_confidence': detection_result.get('detection_confidence')
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    return {
        'annotated_image': annotated_path,
        'metadata_json': json_path
    }
