"""
Email utilities for sending payment receipts
Uses Replit Mail service for reliable email delivery
"""

import os
import sys
import json
import requests
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from db.models import DatabaseManager
from configs.config import DATABASE_PATH

def get_replit_auth_token():
    """Get Replit authentication token for API access"""
    repl_identity = os.environ.get('REPL_IDENTITY')
    web_repl_renewal = os.environ.get('WEB_REPL_RENEWAL')
    
    if repl_identity:
        return f"repl {repl_identity}"
    elif web_repl_renewal:
        return f"depl {web_repl_renewal}"
    else:
        raise Exception("No Replit authentication token found")

def send_replit_email(to_email, subject, html_content, text_content):
    """
    Send email using Replit's mail service
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text email content
    
    Returns:
        dict: API response with email status
    """
    try:
        auth_token = get_replit_auth_token()
        
        payload = {
            "to": to_email,
            "subject": subject,
            "html": html_content,
            "text": text_content
        }
        
        headers = {
            "Content-Type": "application/json",
            "X_REPLIT_TOKEN": auth_token
        }
        
        response = requests.post(
            "https://connectors.replit.com/api/v2/mailer/send",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.ok:
            result = response.json()
            print(f"✅ Email sent successfully to {to_email}")
            print(f"   Message ID: {result.get('messageId', 'N/A')}")
            print(f"   Accepted: {result.get('accepted', [])}")
            return result
        else:
            error_text = response.text
            try:
                error_data = response.json()
                error_message = error_data.get('message', error_text)
            except:
                error_message = error_text
            raise Exception(f"Replit mail API error ({response.status_code}): {error_message}")
            
    except Exception as e:
        print(f"❌ Error sending email via Replit Mail: {e}")
        raise

def send_payment_receipt(to_email, violation_id):
    """
    Send payment receipt email for a violation using Replit Mail
    
    Args:
        to_email (str): Recipient email address
        violation_id (int): Violation ID
        
    Returns:
        bool: Success status
    """
    try:
        # Get violation details
        db = DatabaseManager(DATABASE_PATH)
        violation = db.get_violation_by_id(violation_id)
        
        if not violation:
            print(f"❌ Violation {violation_id} not found")
            return False
        
        # Get owner details
        owner = db.get_owner_by_vehicle(violation['vehicle_no'])
        
        # Create email content
        subject = f"Payment Receipt - Traffic Violation #{violation_id}"
        html_content = create_receipt_email_body(violation, owner)
        text_content = create_receipt_text_body(violation, owner)
        
        # Send email using Replit Mail
        result = send_replit_email(to_email, subject, html_content, text_content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error sending payment receipt: {e}")
        # Fallback: log the receipt details
        print(f"📧 Would send payment receipt to {to_email} for violation #{violation_id}")
        return False

def create_receipt_email_body(violation, owner):
    """
    Create HTML email body for payment receipt
    
    Args:
        violation (dict): Violation details
        owner (dict): Owner details
        
    Returns:
        str: HTML email body
    """
    owner_name = owner['owner_name'] if owner else 'Unknown'
    location = violation.get('location_text', 'Location not specified')
    paid_at = violation.get('paid_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .receipt-box {{ border: 1px solid #ddd; padding: 20px; margin: 20px 0; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
            .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚦 Payment Receipt</h1>
            <h2>Traffic Violation E-Challan</h2>
        </div>
        
        <div class="content">
            <h3>Payment Confirmation</h3>
            <p>Your payment for the following traffic violation has been received:</p>
            
            <div class="receipt-box">
                <table width="100%">
                    <tr>
                        <td><strong>Violation ID:</strong></td>
                        <td>#{violation['id']}</td>
                    </tr>
                    <tr>
                        <td><strong>Vehicle Number:</strong></td>
                        <td>{violation['vehicle_no']}</td>
                    </tr>
                    <tr>
                        <td><strong>Owner Name:</strong></td>
                        <td>{owner_name}</td>
                    </tr>
                    <tr>
                        <td><strong>Violation Type:</strong></td>
                        <td>{violation['violation_type']}</td>
                    </tr>
                    <tr>
                        <td><strong>Location:</strong></td>
                        <td>{location}</td>
                    </tr>
                    <tr>
                        <td><strong>Violation Date:</strong></td>
                        <td>{violation['timestamp']}</td>
                    </tr>
                    <tr>
                        <td><strong>Payment ID:</strong></td>
                        <td>{violation.get('payment_id', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td><strong>Payment Date:</strong></td>
                        <td>{paid_at}</td>
                    </tr>
                    <tr>
                        <td><strong>Fine Amount:</strong></td>
                        <td class="amount">₹{violation['fine_amount']}</td>
                    </tr>
                </table>
            </div>
            
            <p><strong>Status:</strong> <span style="color: #27ae60;">✅ PAID</span></p>
            
            <p>This receipt serves as proof of payment for your traffic violation fine. Please keep this email for your records.</p>
            
            <p>If you have any questions about this payment, please contact the traffic authority.</p>
        </div>
        
        <div class="footer">
            <p>This is an automated email from the Road Safety Violation Detector System.</p>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    
    return html_body

def create_receipt_text_body(violation, owner):
    """
    Create plain text email body for payment receipt
    
    Args:
        violation (dict): Violation details
        owner (dict): Owner details
        
    Returns:
        str: Plain text email body
    """
    owner_name = owner['owner_name'] if owner else 'Unknown'
    location = violation.get('location_text', 'Location not specified')
    paid_at = violation.get('paid_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    text_body = f"""
🚦 PAYMENT RECEIPT - TRAFFIC VIOLATION E-CHALLAN

Payment Confirmation
Your payment for the following traffic violation has been received:

═══════════════════════════════════════════════════════════
VIOLATION DETAILS
═══════════════════════════════════════════════════════════

Violation ID:     #{violation['id']}
Vehicle Number:   {violation['vehicle_no']}
Owner Name:       {owner_name}
Violation Type:   {violation['violation_type']}
Location:         {location}
Violation Date:   {violation['timestamp']}
Payment ID:       {violation.get('payment_id', 'N/A')}
Payment Date:     {paid_at}
Fine Amount:      ₹{violation['fine_amount']}

Status: ✅ PAID

═══════════════════════════════════════════════════════════

This receipt serves as proof of payment for your traffic violation fine. 
Please keep this email for your records.

If you have any questions about this payment, please contact the traffic authority.

---
This is an automated email from the Road Safety Violation Detector System.
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    return text_body.strip()

def test_email_configuration():
    """Test email configuration"""
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASS')
    
    if email_user and email_pass:
        print("✅ Email configuration found")
        print(f"📧 Email user: {email_user}")
        return True
    else:
        print("⚠️  Email configuration missing")
        print("💡 To enable email receipts, set environment variables:")
        print("   EMAIL_USER=your-email@gmail.com")
        print("   EMAIL_PASS=your-app-password")
        print("   SMTP_SERVER=smtp.gmail.com (optional)")
        print("   SMTP_PORT=587 (optional)")
        return False

if __name__ == "__main__":
    test_email_configuration()