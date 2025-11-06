"""
PDF E-Challan Generator for Road Safety Violation Detector
Generates official violation PDFs with embedded images
"""

import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fpdf import FPDF
from db.models import DatabaseManager
from configs.config import DATABASE_PATH, REPORTS_STORAGE

class EchallanPDF(FPDF):
    """Custom PDF class for e-challans"""
    
    def header(self):
        """PDF header"""
        # Logo placeholder (you could add an actual logo here)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'ROAD SAFETY VIOLATION E-CHALLAN', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'Traffic Management System', 0, 1, 'C')
        self.ln(10)
    
    def footer(self):
        """PDF footer"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 0, 'L')
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')

def build_pdf(violation_id):
    """
    Generate PDF e-challan for a violation
    
    Args:
        violation_id (int): Violation ID
        
    Returns:
        str: Path to generated PDF file or None if failed
    """
    try:
        # Get violation details from database
        db = DatabaseManager(DATABASE_PATH)
        violation = db.get_violation_by_id(violation_id)
        
        if not violation:
            print(f"Violation ID {violation_id} not found")
            return None
        
        # Get owner information
        owner = db.get_owner_by_vehicle(violation['vehicle_no'])
        
        # Create PDF
        pdf = EchallanPDF()
        pdf.add_page()
        
        # Title section
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'TRAFFIC VIOLATION NOTICE', 0, 1, 'C')
        pdf.ln(5)
        
        # Violation details section
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'VIOLATION DETAILS', 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Arial', '', 10)
        
        # Two-column layout for details
        col1_x = 10
        col2_x = 110
        
        pdf.set_xy(col1_x, pdf.get_y())
        pdf.cell(90, 8, f'Challan No: #{violation["id"]:06d}', 0, 0, 'L')
        pdf.set_xy(col2_x, pdf.get_y())
        pdf.cell(90, 8, f'Date: {violation["timestamp"][:19]}', 0, 1, 'L')
        
        pdf.set_xy(col1_x, pdf.get_y())
        pdf.cell(90, 8, f'Vehicle No: {violation["vehicle_no"]}', 0, 0, 'L')
        pdf.set_xy(col2_x, pdf.get_y())
        pdf.cell(90, 8, f'Fine Amount: Rs. {violation["fine_amount"]}', 0, 1, 'L')
        
        if owner:
            pdf.set_xy(col1_x, pdf.get_y())
            pdf.cell(90, 8, f'Owner Name: {owner["owner_name"]}', 0, 0, 'L')
        
        # Payment status
        if violation.get('paid'):
            pdf.set_xy(col2_x, pdf.get_y())
            pdf.set_text_color(0, 128, 0)  # Green color
            pdf.cell(90, 8, 'STATUS: PAID', 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)  # Reset to black
        else:
            pdf.set_xy(col2_x, pdf.get_y())
            pdf.set_text_color(255, 0, 0)  # Red color
            pdf.cell(90, 8, 'STATUS: UNPAID', 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)  # Reset to black
        
        # Location if available
        if violation.get('location_text'):
            pdf.set_xy(col1_x, pdf.get_y())
            pdf.cell(180, 8, f'Location: {violation["location_text"]}', 0, 1, 'L')
        
        pdf.ln(5)
        
        # Violation type section
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'VIOLATION TYPE', 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 8, violation['violation_type'], 0, 1, 'L')
        
        if violation['description']:
            pdf.ln(3)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 5, violation['description'])
        
        pdf.ln(10)
        
        # Image section - with proper path resolution
        image_path = None
        if violation['image_path']:
            # Try different path resolutions
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go to project root
            possible_paths = [
                violation['image_path'],  # Try as absolute path first
                os.path.join(base_path, 'storage', 'violations', violation['image_path']),  # Storage directory
                os.path.join(base_path, 'media', 'violations', violation['image_path']),  # Media directory
                os.path.join(base_path, violation['image_path'].lstrip('/')),  # Root relative path
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    image_path = path
                    break
        
        if image_path:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'VIOLATION EVIDENCE', 0, 1, 'L')
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            
            try:
                # Add image to PDF
                img_width = 120
                img_height = 80
                pdf.image(image_path, x=45, y=pdf.get_y(), w=img_width, h=img_height)
                pdf.ln(img_height + 10)
                print(f"✅ Image added to PDF: {image_path}")
            except Exception as e:
                print(f"❌ Could not add image to PDF: {e}")
                pdf.cell(0, 8, '[Image could not be embedded]', 0, 1, 'L')
                pdf.ln(5)
        else:
            print(f"❌ Image not found for paths: {violation['image_path']}")
            # Still add the evidence section but with a note
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'VIOLATION EVIDENCE', 0, 1, 'L')
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 8, '[Evidence image not available]', 0, 1, 'L')
            pdf.ln(5)
        
        # Fine details section
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'FINE DETAILS', 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, f'Fine Amount: Rs. {violation["fine_amount"]}', 0, 1, 'L')
        
        # Payment information
        if violation.get('paid'):
            pdf.set_text_color(0, 128, 0)  # Green color
            pdf.cell(0, 8, f'Payment Status: PAID', 0, 1, 'L')
            pdf.cell(0, 8, f'Payment ID: {violation.get("payment_id", "N/A")}', 0, 1, 'L')
            pdf.cell(0, 8, f'Payment Date: {violation.get("paid_at", "N/A")}', 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)  # Reset to black
        else:
            pdf.set_text_color(255, 0, 0)  # Red color
            pdf.cell(0, 8, 'Payment Status: UNPAID', 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)  # Reset to black
            pdf.cell(0, 8, 'Payment due within 15 days from the date of issue', 0, 1, 'L')
        
        pdf.ln(5)
        
        # Instructions section
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'PAYMENT INSTRUCTIONS', 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Arial', '', 9)
        instructions = [
            '1. Pay the fine within 15 days to avoid additional charges',
            '2. Visit the nearest traffic police station for payment',
            '3. Keep this challan as proof of payment',
            '4. For any queries, contact the traffic helpline'
        ]
        
        for instruction in instructions:
            pdf.cell(0, 6, instruction, 0, 1, 'L')
        
        pdf.ln(10)
        
        # Authority section
        pdf.set_font('Arial', 'I', 9)
        pdf.cell(0, 6, 'This is a computer-generated challan and does not require a signature.', 0, 1, 'C')
        
        # Save PDF
        os.makedirs(REPORTS_STORAGE, exist_ok=True)
        pdf_filename = f"challan_{violation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(REPORTS_STORAGE, pdf_filename)
        
        pdf.output(pdf_path)
        
        # Update database with PDF path
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE violations SET pdf_path = ? WHERE id = ?', (pdf_path, violation_id))
        conn.commit()
        conn.close()
        
        print(f"PDF generated: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

def generate_sample_pdf():
    """Generate a sample PDF for testing"""
    # Create a test violation if none exist
    db = DatabaseManager(DATABASE_PATH)
    
    # Check if we have any violations
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM violations LIMIT 1')
    violation = cursor.fetchone()
    conn.close()
    
    if violation:
        violation_id = violation[0]
    else:
        # Create a sample violation
        violation_id = db.insert_violation(
            vehicle_no='MH01AB1234',
            violation_type='NO_HELMET',
            fine_amount=500,
            description='Rider observed without helmet on main road'
        )
    
    return build_pdf(violation_id)

if __name__ == "__main__":
    # Test PDF generation
    pdf_path = generate_sample_pdf()
    if pdf_path:
        print(f"Sample PDF generated at: {pdf_path}")
    else:
        print("Failed to generate sample PDF")