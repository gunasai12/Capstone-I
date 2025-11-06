"""
PaddleOCR-based license plate recognition
Superior accuracy compared to EasyOCR for Indian plates
"""

import sys
import os
import cv2
import re
from typing import Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class PaddleOCRReader:
    """License plate reader using PaddleOCR"""
    
    def __init__(self):
        self.reader = None
        self.load_ocr()
    
    def load_ocr(self):
        """Load PaddleOCR model"""
        try:
            from paddleocr import PaddleOCR
            self.reader = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            print("PaddleOCR loaded successfully")
        except ImportError:
            print("PaddleOCR not available. Falling back to EasyOCR")
            self.reader = None
        except Exception as e:
            print(f"Error loading PaddleOCR: {e}")
            self.reader = None
    
    def read_plate(self, image):
        """
        Read license plate text from image
        
        Args:
            image (numpy.ndarray): Input image containing number plate
            
        Returns:
            tuple: (plate_text, confidence) or ('UNKNOWN', 0.0)
        """
        if image is None or image.size == 0:
            return 'UNKNOWN', 0.0
        
        try:
            if self.reader is not None:
                return self._paddle_ocr(image)
            else:
                # Fallback to EasyOCR if PaddleOCR not available
                return self._easyocr_fallback(image)
        except Exception as e:
            print(f"OCR error: {e}")
            return 'UNKNOWN', 0.0
    
    def _paddle_ocr(self, image):
        """Use PaddleOCR to extract text"""
        try:
            result = self.reader.ocr(image, cls=True)
            
            # Extract highest confidence text
            best_text = ""
            best_conf = 0.0
            
            if result and result[0]:
                for line in result[0]:
                    if line:
                        text = line[1][0]
                        conf = float(line[1][1])
                        if conf > best_conf:
                            best_text = text
                            best_conf = conf
            
            # Clean and normalize the text
            plate_text = self._normalize_plate_text(best_text)
            
            return plate_text, best_conf
            
        except Exception as e:
            print(f"PaddleOCR processing error: {e}")
            return 'UNKNOWN', 0.0
    
    def _easyocr_fallback(self, image):
        """Fallback to EasyOCR if PaddleOCR unavailable"""
        try:
            import easyocr
            reader = easyocr.Reader(['en'], verbose=False)
            results = reader.readtext(image)
            
            if results:
                # Get highest confidence result
                best_result = max(results, key=lambda x: x[2])
                text = best_result[1]
                conf = best_result[2]
                plate_text = self._normalize_plate_text(text)
                return plate_text, conf
            else:
                return 'UNKNOWN', 0.0
                
        except Exception as e:
            print(f"EasyOCR fallback error: {e}")
            return 'UNKNOWN', 0.0
    
    def _normalize_plate_text(self, text: str) -> str:
        """
        Normalize license plate text to Indian format
        Format: AB12CD3456 (State Code + District + Series + Number)
        """
        if not text:
            return 'UNKNOWN'
        
        # Remove spaces and special characters
        clean_text = re.sub(r'[^A-Z0-9]', '', text.upper())
        
        # Validate basic pattern (2 letters, 2 digits, 1-2 letters, 4 digits)
        # This matches Indian license plate format
        indian_plate_pattern = r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$'
        
        if re.match(indian_plate_pattern, clean_text):
            return clean_text
        
        # If it doesn't match but has reasonable length, return it anyway
        if 8 <= len(clean_text) <= 10:
            return clean_text
        
        # Otherwise return UNKNOWN
        return 'UNKNOWN' if len(clean_text) < 5 else clean_text


def extract_plate_text(image_crop) -> Tuple[str, float]:
    """
    Extract plate text from cropped image
    
    Args:
        image_crop (numpy.ndarray): Cropped license plate region
        
    Returns:
        tuple: (plate_text, confidence)
    """
    reader = PaddleOCRReader()
    return reader.read_plate(image_crop)


def crop_from_bbox(img, bbox):
    """Extract region from image using bounding box"""
    x1, y1, x2, y2 = bbox
    h, w = img.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w - 1, x2)
    y2 = min(h - 1, y2)
    return img[y1:y2, x1:x2]
