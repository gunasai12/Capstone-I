"""
OCR service wrapper for web app integration  
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from road_safety_violation_detector.website.plate_reader import PlateReader

def extract_plate_number(image_path):
    """
    Extract license plate number from image
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        str: Extracted license plate number or None
    """

    import cv2
    
    # Read image
    image = cv2.imread(image_path)
    if image is None:
        return None
    
    # Initialize plate reader
    reader = PlateReader()
    
    # Extract plate
    plate_text = reader.read_plate(image)
    
    return plate_text if plate_text != 'UNKNOWN' else None