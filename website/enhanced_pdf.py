"""
Enhanced PDF generation with annotated images and professional formatting
Uses ReportLab for high-quality violation reports
"""

import os
import sys
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Fine amounts
FINES = {
    "helmet_violation": 500,   # First offense
    "no_helmet": 1000,         # Repeat offense
    "triple_riding": 1000
}


def generate_enhanced_pdf(evidence: dict, output_dir: str, annotated_image_path: str, violation_id: str = None):
    """
    Generate professional PDF report with annotated images
    
    Args:
        evidence: Dictionary containing violation metadata
        output_dir: Directory to save PDF
        annotated_image_path: Path to annotated evidence image
        violation_id: Optional violation ID
        
    Returns:
        str: Path to generated PDF
    """
    timestamp = evidence.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
    pdf_name = f"challan_{violation_id or timestamp}.pdf"
    pdf_path = os.path.join(output_dir, pdf_name)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    
    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30, height - 50, "TRAFFIC VIOLATION E-CHALLAN")
    
    # Underline
    c.line(30, height - 55, width - 30, height - 55)
    
    y = height - 90
    c.setFont("Helvetica", 11)
    
    # Violation ID
    if violation_id:
        c.drawString(30, y, f"Challan ID: {violation_id}")
        y -= 20
    
    # Date & Time
    c.drawString(30, y, f"Date & Time: {timestamp}")
    y -= 20
    
    # License Plate
    plate = evidence.get("license_plate", {})
    if isinstance(plate, dict):
        plate_text = plate.get('text', 'UNKNOWN')
        plate_conf = plate.get('confidence', 0) * 100
    else:
        plate_text = str(plate)
        plate_conf = 0
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, f"License Plate: {plate_text}")
    if plate_conf > 0:
        c.setFont("Helvetica", 10)
        c.drawString(200, y, f"(Confidence: {plate_conf:.1f}%)")
    y -= 30
    
    # Violations section
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y, "Detected Violations:")
    y -= 25
    
    total_fine = 0
    violations = evidence.get("violations", [])
    
    c.setFont("Helvetica", 11)
    if violations:
        for v in violations:
            v_type = v.get("type", "unknown")
            fine_amt = FINES.get(v_type, 500)
            total_fine += fine_amt
            
            violation_name = v_type.replace('_', ' ').title()
            c.drawString(50, y, f"• {violation_name}")
            c.drawString(300, y, f"Fine: ₹{fine_amt}")
            y -= 20
    else:
        c.drawString(50, y, "No violations detected.")
        y -= 20
    
    # Total fine
    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, y, f"Total Fine Amount: ₹{total_fine}")
    y -= 30
    
    # Payment status
    payment_status = evidence.get("payment_status", "Pending")
    c.setFont("Helvetica", 11)
    c.drawString(30, y, f"Payment Status: {payment_status.upper()}")
    y -= 20
    
    # Location (if available)
    location = evidence.get("location", "AI Detection System")
    c.drawString(30, y, f"Location: {location}")
    y -= 40
    
    # Evidence image
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "Evidence Image:")
    y -= 10
    
    if os.path.exists(annotated_image_path):
        try:
            # Add annotated image with violations marked
            img_height = 300
            img_width = width - 60
            y_img = y - img_height
            
            if y_img > 50:  # Check if there's space
                c.drawImage(annotated_image_path, 30, y_img, 
                           width=img_width, height=img_height, 
                           preserveAspectRatio=True, mask='auto')
            else:
                # Start new page if needed
                c.showPage()
                c.drawImage(annotated_image_path, 30, height - 400, 
                           width=img_width, height=300,
                           preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Error adding image to PDF: {e}")
            c.drawString(30, y - 20, "[Image could not be embedded]")
    else:
        c.drawString(30, y - 20, "[Evidence image not available]")
    
    # Footer
    c.setFont("Helvetica", 9)
    footer_text = "This is a computer-generated e-challan. AI-powered traffic enforcement system."
    c.drawString(30, 30, footer_text)
    
    c.showPage()
    c.save()
    
    return pdf_path


def generate_simple_pdf(violation_data: dict, output_path: str):
    """
    Generate simple PDF report (backward compatibility)
    
    Args:
        violation_data: Violation information
        output_path: Path to save PDF
        
    Returns:
        str: Path to generated PDF
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, height - 50, "Traffic Violation Report")
    
    y = height - 100
    c.setFont("Helvetica", 11)
    
    for key, value in violation_data.items():
        c.drawString(30, y, f"{key}: {value}")
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    
    c.save()
    return output_path
