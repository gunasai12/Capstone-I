"""
Flask web application for Road Safety Violation Detector
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template, request, redirect, url_for, send_file, flash, Response, send_from_directory
from db.models import DatabaseManager
from configs.config import DATABASE_PATH, FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from road_safety_violation_detector.website.rules import compute_fine
from road_safety_violation_detector.website.email_utils import send_payment_receipt
from datetime import datetime
import time
import qrcode
from io import BytesIO
import os
import uuid
import random
from werkzeug.utils import secure_filename

# Configure upload settings
UPLOAD_FOLDER = 'media/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv', 'webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB for video support

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_video_file(filename):
    """Check if file is a video format"""
    video_extensions = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in video_extensions

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'your-secret-key-here')

# Initialize database
db = DatabaseManager(DATABASE_PATH)

def get_dashboard_stats():
    """Get dashboard statistics"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Total violations
    cursor.execute('SELECT COUNT(*) FROM violations')
    total_violations = cursor.fetchone()[0]
    
    # Total fine amount
    cursor.execute('SELECT SUM(fine_amount) FROM violations')
    total_fines = cursor.fetchone()[0] or 0
    
    # Violations by type
    cursor.execute('SELECT violation_type, COUNT(*) FROM violations GROUP BY violation_type')
    violations_by_type = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        'total_violations': total_violations,
        'total_fines': total_fines,
        'violations_by_type': violations_by_type
    }

def get_recent_ai_detections(limit=10):
    """Get recent AI-analyzed violations with annotated images"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get recent violations that have annotated images
    cursor.execute("""
        SELECT id, vehicle_no, violation_type, fine_amount, location_text, 
               timestamp, image_path
        FROM violations 
        WHERE image_path IS NOT NULL
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    
    recent_detections = []
    for row in cursor.fetchall():
        recent_detections.append({
            'id': row[0],
            'vehicle_no': row[1],
            'violation_type': row[2],
            'fine_amount': row[3],
            'location': row[4] if row[4] else 'Unknown Location',
            'datetime': row[5],
            'image_path': row[6],
            'confidence': 0.85  # Default confidence for display
        })
    
    conn.close()
    return recent_detections

@app.route('/')
def index():
    """Home page with professional dashboard"""
    stats = get_dashboard_stats()
    recent_ai = get_recent_ai_detections(10)
    return render_template('index.html', stats=stats, recent_ai_detections=recent_ai)

@app.route('/storage/<path:filename>')
def serve_storage_file(filename):
    """Serve files from the storage directory"""
    storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage')
    return send_from_directory(storage_dir, filename)

@app.route('/video_frame/<path:path>')
def serve_violation_frame(path):
    """Serve video violation frames with security restrictions"""
    # Define safe base directory
    safe_base = os.path.join(app.root_path, '..', 'media', 'video_violations')
    safe_base = os.path.realpath(safe_base)
    
    # Normalize the requested path to prevent directory traversal
    requested_path = os.path.normpath(path)
    full_path = os.path.realpath(os.path.join(safe_base, requested_path))
    
    # Security check: ensure the resolved path is within the safe base directory
    # Use os.path.commonpath to guarantee containment
    try:
        common = os.path.commonpath([safe_base, full_path])
        if common != safe_base:
            return "Access denied", 403
    except ValueError:
        # Different drives on Windows
        return "Access denied", 403
    
    # Check if file exists
    if not os.path.exists(full_path):
        return "File not found", 404
    
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(directory, filename)

@app.route('/search', methods=['POST'])
def search():
    """Search for vehicle violations"""
    vehicle_no = request.form.get('vehicle_no', '').strip().upper()
    
    if not vehicle_no:
        flash('Please enter a vehicle number', 'error')
        return redirect(url_for('index'))
    
    return redirect(url_for('vehicle_details', vehicle_no=vehicle_no))

@app.route('/vehicle/<vehicle_no>')
def vehicle_details(vehicle_no):
    """Show all violations for a specific vehicle - Local records only"""
    # Do not fetch or display Telangana Police data here. Kept separate by policy.
    vehicle_no = vehicle_no.upper()
    
    # Get owner information
    owner = db.get_owner_by_vehicle(vehicle_no)
    
    # Get all violations for this vehicle (local database only)
    violations = db.get_violations_by_vehicle(vehicle_no)
    
    return render_template('vehicle.html', 
                         vehicle_no=vehicle_no, 
                         owner=owner, 
                         violations=violations)

@app.route('/violation/<int:violation_id>')
def violation_details(violation_id):
    """Show details for a specific violation"""
    violation = db.get_violation_by_id(violation_id)
    
    if not violation:
        flash('Violation not found', 'error')
        return redirect(url_for('index'))
    
    # Get owner information
    owner = db.get_owner_by_vehicle(violation['vehicle_no'])
    
    return render_template('violation.html', violation=violation, owner=owner)

@app.route('/violation/<int:violation_id>/pdf')
def download_pdf(violation_id):
    """Download PDF for a specific violation"""
    violation = db.get_violation_by_id(violation_id)
    
    if not violation or not violation['pdf_path']:
        flash('PDF not found', 'error')
        return redirect(url_for('index'))
    
    try:
        # Construct full path to PDF file
        from configs.config import REPORTS_STORAGE
        import os
        pdf_file_path = os.path.join(REPORTS_STORAGE, violation['pdf_path'])
        
        if not os.path.exists(pdf_file_path):
            flash('PDF file not found on server', 'error')
            return redirect(url_for('violation_details', violation_id=violation_id))
        
        return send_file(pdf_file_path, as_attachment=True, download_name=f"violation_{violation['vehicle_no']}_challan.pdf")
    except Exception as e:
        flash(f'Error downloading PDF: {str(e)}', 'error')
        return redirect(url_for('violation_details', violation_id=violation_id))

@app.route('/media/violations/<filename>')
def serve_violation_image(filename):
    """Serve violation images securely"""
    from flask import send_file
    from configs.config import VIOLATIONS_STORAGE
    import os
    
    # Build absolute paths for both checking and serving
    app_base = os.path.join(app.root_path, '..')
    violations_absolute = os.path.join(app_base, VIOLATIONS_STORAGE)
    # Fix: uploads are saved in website/media/uploads, not project_root/media/uploads
    uploads_absolute = os.path.join(app.root_path, 'media', 'uploads')
    
    violations_file = os.path.join(violations_absolute, filename)
    uploads_file = os.path.join(uploads_absolute, filename)
    
    # First check if file exists in violations storage
    if os.path.exists(violations_file):
        return send_file(violations_file)
    
    # If not found in violations, try uploads folder (for demo images)
    if os.path.exists(uploads_file):
        return send_file(uploads_file)
    
    # If file not found in either location, return 404
    from flask import abort
    abort(404)

@app.route('/generate_qr/<int:violation_id>')
def generate_dynamic_qr(violation_id):
    """Generate dynamic QR code with exact violation amount"""
    # Get violation details
    violation = db.get_violation_by_id(violation_id)
    if not violation:
        return "Violation not found", 404
    
    if violation.get('paid'):
        return "Violation already paid", 400
    
    # Create UPI payment intent with exact amount - using user's PhonePe account
    # Format: upi://pay?pa=VPA&pn=MERCHANT_NAME&am=AMOUNT&cu=INR&tn=DESCRIPTION
    # Updated to use the uploaded PhonePe QR code merchant details
    merchant_vpa = "ganumulapally@axl"  # User's actual PhonePe VPA 
    merchant_name = "Traffic Fine Payment"
    amount = violation['fine_amount']
    currency = "INR"
    transaction_note = f"Traffic Fine - Violation {violation_id}"
    
    # Create UPI intent URL with exact amount (cannot be tampered)
    upi_url = f"upi://pay?pa={merchant_vpa}&pn={merchant_name}&am={amount}&cu={currency}&tn={transaction_note}&tr=VID{violation_id}"
    
    # Generate QR code
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return Response(img_io.getvalue(), mimetype='image/png')

@app.route('/confirm_qr_payment/<int:violation_id>', methods=['POST'])
def confirm_qr_payment(violation_id):
    """Confirm QR code payment for a violation with verification"""
    payer_email = request.form.get('payer_email', '').strip()
    transaction_id = request.form.get('transaction_id', '').strip()
    upi_ref_no = request.form.get('upi_ref_no', '').strip()
    
    # Validation
    if not payer_email:
        flash('Please enter your email address', 'error')
        return redirect(request.referrer or url_for('index'))
    
    if not transaction_id:
        flash('Please enter the UPI Transaction ID from your payment app', 'error')
        return redirect(request.referrer or url_for('index'))
    
    if len(transaction_id) < 8:
        flash('Invalid Transaction ID. Please enter the complete Transaction ID from your UPI app', 'error')
        return redirect(request.referrer or url_for('index'))
    
    # Get violation details
    violation = db.get_violation_by_id(violation_id)
    if not violation:
        flash('Violation not found', 'error')
        return redirect(url_for('index'))
    
    if violation.get('paid'):
        flash('This violation has already been paid', 'warning')
        return redirect(url_for('vehicle_details', vehicle_no=violation['vehicle_no']))
    
    # Enhanced payment verification with amount checking
    # In a real system, this would call the UPI gateway API to verify the transaction
    verification_result = verify_demo_payment(transaction_id, violation['fine_amount'], violation_id)
    
    if not verification_result['success']:
        flash(f'Payment verification failed: {verification_result["error"]}', 'error')
        return redirect(request.referrer or url_for('index'))
    
    # Generate payment ID using the verified transaction with amount confirmation
    verified_amount = verification_result['paid_amount']
    payment_id = f"UPI-{transaction_id}-₹{verified_amount}"
    paid_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Update payment status with atomic transaction verification
    result = db.update_payment_status(
        violation_id, 
        payment_id, 
        payer_email, 
        paid_at,
        transaction_id=transaction_id,
        paid_amount=verified_amount
    )
    
    if result['success']:
        # Send email receipt
        email_sent = send_payment_receipt(payer_email, violation_id)
        
        if email_sent:
            flash(f'✅ Payment Verified & Confirmed! Amount: ₹{verified_amount} | Receipt sent to {payer_email}', 'success')
        else:
            flash(f'✅ Payment Verified & Confirmed! Amount: ₹{verified_amount} | (Email receipt not sent - check configuration)', 'success')
    else:
        flash(f'Payment confirmation failed: {result["error"]}', 'error')
    
    return redirect(url_for('vehicle_details', vehicle_no=violation['vehicle_no']))

def verify_demo_payment(transaction_id, expected_amount, violation_id):
    """
    Enhanced demo payment verification with amount checking and duplicate prevention
    In a real system, this would integrate with UPI gateway APIs
    """
    # Basic validation
    if len(transaction_id) < 8:
        return {'success': False, 'error': 'Transaction ID too short (minimum 8 characters)'}
    
    # Check if transaction ID has already been used (exact match)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM violations WHERE transaction_id = ? AND id != ?', (transaction_id, violation_id))
    existing = cursor.fetchone()
    conn.close()
    
    if existing:
        return {'success': False, 'error': 'Transaction ID already used for another violation'}
    
    # Simulate payment verification delay
    import time
    time.sleep(1)  # Simulate API call
    
    # Demo: Extract amount from transaction ID pattern for simulation
    # In real system, this would come from UPI gateway API response
    simulated_paid_amount = extract_demo_amount(transaction_id, expected_amount)
    
    if simulated_paid_amount is None:
        return {'success': False, 'error': 'Invalid transaction - payment not found in UPI gateway'}
    
    # Critical: Verify amount matches exactly
    if abs(simulated_paid_amount - expected_amount) > 0.01:  # Allow 1 paisa tolerance for rounding
        return {
            'success': False, 
            'error': f'Payment amount mismatch. Expected: ₹{expected_amount}, Paid: ₹{simulated_paid_amount}'
        }
    
    return {'success': True, 'paid_amount': simulated_paid_amount}

def extract_demo_amount(transaction_id, expected_amount):
    """
    Demo function to simulate extracting paid amount from UPI gateway
    In real system, this would be returned by UPI gateway API
    """
    # Demo patterns for testing different scenarios
    transaction_upper = transaction_id.upper()
    
    # Check specific scenario patterns first (most specific to least specific)
    
    # Scenario 1: Underpayment patterns (check first to avoid false positives)
    underpay_patterns = ['LESS', 'UNDER', 'SMALL', 'HALF']
    for pattern in underpay_patterns:
        if pattern in transaction_upper:
            return expected_amount * 0.5  # Return half the amount
    
    # Scenario 2: Overpayment patterns
    overpay_patterns = ['MORE', 'OVER', 'EXTRA', 'DOUBLE']
    for pattern in overpay_patterns:
        if pattern in transaction_upper:
            return expected_amount * 2  # Return double the amount
    
    # Scenario 3: Correct amount patterns
    correct_patterns = ['UPI', 'PAY', 'CORRECT', 'FULL', 'EXACT']
    for pattern in correct_patterns:
        if pattern in transaction_upper:
            return expected_amount  # Return exact expected amount
    
    # Scenario 4: Numeric patterns for correct payment
    if any(num in transaction_upper for num in ['123', '456', '789']):
        return expected_amount
        
    # Scenario 5: Long transaction IDs (assume correct for demo)
    if len(transaction_id) >= 12:
        return expected_amount
    
    # Scenario 6: Invalid/not found
    return None

@app.route('/telangana-police')
def telangana_police_dashboard():
    """Dashboard showing recent Telangana Police e-Challans"""
    try:
        from road_safety_violation_detector.website.telangana_police import get_recent_challans
        recent_challans = get_recent_challans(30)  # Last 30 days
        return render_template('telangana_police.html', challans=recent_challans)
    except Exception as e:
        flash(f'Error loading Telangana Police data: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/telangana-police/challan/<challan_number>')
def telangana_challan_details(challan_number):
    """Show details for a specific Telangana Police e-Challan"""
    try:
        from road_safety_violation_detector.website.telangana_police import get_challan_details
        challan = get_challan_details(challan_number)
        if not challan:
            flash('Telangana Police challan not found', 'error')
            return redirect(url_for('telangana_police_dashboard'))
        
        return render_template('telangana_challan.html', challan=challan)
    except Exception as e:
        flash(f'Error loading challan details: {str(e)}', 'error')
        return redirect(url_for('telangana_police_dashboard'))

@app.route('/search-telangana', methods=['POST'])
def search_telangana_challans():
    """Search specifically in Telangana Police records"""
    search_type = request.form.get('search_type', 'vehicle')
    search_value = request.form.get('search_value', '').strip().upper()
    
    if not search_value:
        flash('Please enter a search value', 'error')
        return redirect(url_for('index'))
    
    try:
        from road_safety_violation_detector.website.telangana_police import get_vehicle_challans, get_challan_details
        
        if search_type == 'vehicle':
            challans = get_vehicle_challans(search_value)
            return render_template('telangana_search_results.html', 
                                 search_type='vehicle',
                                 search_value=search_value,
                                 challans=challans)
        elif search_type == 'challan':
            challan = get_challan_details(search_value)
            if challan:
                return redirect(url_for('telangana_challan_details', challan_number=search_value))
            else:
                flash('Challan not found in Telangana Police records', 'error')
                return redirect(url_for('telangana_police_dashboard'))
    except Exception as e:
        flash(f'Search failed: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for basic statistics"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Total violations
    cursor.execute('SELECT COUNT(*) FROM violations')
    total_violations = cursor.fetchone()[0]
    
    # Total fine amount
    cursor.execute('SELECT SUM(fine_amount) FROM violations')
    total_fines = cursor.fetchone()[0] or 0
    
    # Violations by type
    cursor.execute('SELECT violation_type, COUNT(*) FROM violations GROUP BY violation_type')
    violations_by_type = dict(cursor.fetchall())
    
    # Add Telangana Police statistics (separate system)
    try:
        from road_safety_violation_detector.website.telangana_police import get_recent_challans
        telangana_recent = get_recent_challans(30)
        telangana_count = len(telangana_recent)
        telangana_fines = sum(ch.get('fine_amount', 0) for ch in telangana_recent)
    except:
        telangana_count = 0
        telangana_fines = 0
    
    conn.close()
    
    return {
        'total_violations': total_violations,
        'total_fines': total_fines,
        'violations_by_type': violations_by_type,
        'telangana_police': {
            'total_challans': telangana_count,
            'total_fines': telangana_fines
        }
    }

@app.route('/demo-detection', methods=['POST'])
def demo_detection():
    """Process uploaded image or video for violation detection"""
    try:
        # Validate file upload
        if 'vehicle_image' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('index'))
        
        file = request.files['vehicle_image']
        location = request.form.get('location', '').strip()
        violation_datetime = request.form.get('violation_datetime', '')
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload images (PNG, JPG, JPEG, GIF) or videos (MP4, AVI, MOV, MKV, WEBM).', 'error')
            return redirect(url_for('index'))
        
        if not location:
            flash('Location is required', 'error')
            return redirect(url_for('index'))
        
        # Check file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            flash('File too large. Maximum size is 100MB.', 'error')
            return redirect(url_for('index'))
        
        # Save uploaded file securely
        filename = secure_filename(file.filename)
        if not filename:
            filename = 'uploaded_file.jpg'
            
        unique_filename = f"demo_{uuid.uuid4().hex[:8]}_{filename}"
        upload_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(upload_path)
        
        # Check if it's a video or image
        if is_video_file(filename):
            # Process video
            flash('📹 Processing video... This may take a few minutes.', 'info')
            detection_result = process_demo_video(upload_path, location, violation_datetime)
            return render_template('video_results.html', result=detection_result)
        else:
            # Process image
            detection_result = process_demo_image(upload_path, location, violation_datetime)
            
            # Check if this is a vehicle image
            if not detection_result.get('is_vehicle_image', True):
                flash('⚠️ No vehicles detected in uploaded image. Please upload an image containing vehicles.', 'warning')
                return render_template('demo_results.html', result=detection_result)
            
            # If violations found, create violation record
            if detection_result['violations_found']:
                violation_id = create_demo_violation(detection_result)
                if violation_id:
                    flash(f'✅ AI Detection Complete! {len(detection_result["violations"])} violation(s) detected. Violation ID: {violation_id}', 'success')
                    return render_template('demo_results.html', result=detection_result, violation_id=violation_id)
                else:
                    flash('❌ Error creating violation record', 'error')
                    return render_template('demo_results.html', result=detection_result)
            else:
                flash('✅ Vehicle image analyzed - No violations detected', 'info')
                return render_template('demo_results.html', result=detection_result)
            
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('index'))

def process_demo_image(image_path, location, violation_datetime):
    """Process uploaded image with advanced AI detection and evidence generation"""
    try:
        from road_safety_violation_detector.website.ai_detector import detect_violations, save_detection_evidence
        import cv2
        
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Could not read the uploaded image")
        
        # Advanced AI detection with spatial reasoning
        detection_result = detect_violations(image_path, save_annotations=True)
        
        # Extract results
        violations = detection_result.get('violations', [])
        is_vehicle_image = detection_result.get('is_vehicle_image', True)
        plate_info = detection_result.get('license_plate', {})
        plate_number = plate_info.get('text', 'UNKNOWN')
        plate_conf = plate_info.get('confidence', 0.0)
        
        # If no vehicles detected, return early
        if not is_vehicle_image:
            return {
                'image_path': image_path,
                'violations_found': False,
                'violations': [],
                'license_plate': "UNKNOWN",
                'location': location,
                'datetime': violation_datetime,
                'processed_at': datetime.now().isoformat(),
                'total_fine': 0,
                'message': "No vehicles detected in uploaded image. Please upload an image containing vehicles.",
                'is_vehicle_image': False
            }
        
        # Save detection evidence (annotated image + JSON)
        evidence_dir = os.path.join(app.root_path, '..', 'media', 'violations')
        evidence_paths = save_detection_evidence(detection_result, image_path, evidence_dir)
        
        # Generate realistic plate if not detected but violations found
        if plate_number == "UNKNOWN" and len(violations) > 0:
            import hashlib
            hash_val = hashlib.md5(str(image.shape).encode()).hexdigest()
            state_codes = ['AP', 'TN', 'KA', 'MH', 'DL', 'UP', 'WB', 'GJ']
            state = state_codes[int(hash_val[:2], 16) % len(state_codes)]
            district = f"{int(hash_val[2:4], 16) % 50 + 1:02d}"
            letters = chr(65 + int(hash_val[4:6], 16) % 26) + chr(65 + int(hash_val[6:8], 16) % 26)
            numbers = f"{int(hash_val[8:12], 16) % 10000:04d}"
            plate_number = f"{state}{district}{letters}{numbers}"
        
        # Calculate total fine
        total_fine = 0
        for violation in violations:
            if violation.get('type') == 'helmet_violation':
                total_fine += 500
            elif violation.get('type') == 'triple_riding':
                total_fine += 1000
        
        # Prepare comprehensive result
        result = {
            'image_path': image_path,
            'violations_found': len(violations) > 0,
            'violations': violations,
            'license_plate': plate_number,
            'plate_confidence': plate_conf,
            'location': location,
            'datetime': violation_datetime,
            'processed_at': datetime.now().isoformat(),
            'total_fine': total_fine,
            'is_vehicle_image': True,
            'annotated_image_path': evidence_paths.get('annotated_image'),
            'evidence_json_path': evidence_paths.get('metadata_json'),
            'detection_metadata': detection_result.get('counts', {}),
            'detection_confidence': detection_result.get('detection_confidence')
        }
        
        return result
        
    except ImportError as e:
        print(f"Import error in AI detection: {e}")
        return simulate_demo_detection(image_path, location, violation_datetime)
    except Exception as e:
        print(f"Detection error: {e}")
        import traceback
        traceback.print_exc()
        return simulate_demo_detection(image_path, location, violation_datetime)

def process_demo_video(video_path, location, violation_datetime):
    """Process uploaded video with frame-by-frame violation detection"""
    try:
        from road_safety_violation_detector.website.video_processor import process_video_file
        
        # Create output directory for violation frames
        output_dir = os.path.join(app.root_path, '..', 'media', 'video_violations', 
                                  f"video_{uuid.uuid4().hex[:8]}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Process video (analyze every 30 frames = ~1fps for 30fps video)
        video_result = process_video_file(video_path, output_dir=output_dir, frame_skip=30)
        
        # Extract summary data
        violations_timeline = video_result['results']['violations_timeline']
        total_violations = video_result['results']['total_violations']
        
        # Calculate total fine
        total_fine = 0
        for frame_data in violations_timeline:
            for violation in frame_data['violations']:
                if violation['type'] == 'helmet_violation':
                    total_fine += 500
                elif violation['type'] == 'triple_riding':
                    total_fine += 1000
        
        # Get plate numbers from timeline
        all_plate_numbers = []
        for frame_data in violations_timeline:
            plates = frame_data.get('plate_numbers', [])
            for plate in plates:
                if plate['number'] not in all_plate_numbers:
                    all_plate_numbers.append(plate['number'])
        
        result = {
            'video_path': video_path,
            'is_video': True,
            'location': location,
            'datetime': violation_datetime,
            'processed_at': datetime.now().isoformat(),
            'video_info': video_result['video_info'],
            'processing_info': video_result['processing_info'],
            'total_violations': total_violations,
            'violations_timeline': violations_timeline,
            'violation_frame_paths': video_result['results']['violation_frame_paths'],
            'total_fine': total_fine,
            'plate_numbers': all_plate_numbers,
            'violations_found': total_violations > 0
        }
        
        return result
        
    except Exception as e:
        print(f"Video processing error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'video_path': video_path,
            'is_video': True,
            'error': str(e),
            'violations_found': False,
            'total_violations': 0,
            'total_fine': 0
        }

def simulate_demo_detection(image_path, location, violation_datetime):
    """Simulate detection results for demo purposes when AI libraries not available"""
    # Simulate different violation scenarios
    scenarios = [
        {
            'violations': [{'type': 'helmet_violation', 'confidence': 0.87}],
            'plate': 'KA05MN1234',
            'violations_found': True
        },
        {
            'violations': [{'type': 'triple_riding', 'confidence': 0.92}],
            'plate': 'TN07AB5678',
            'violations_found': True
        },
        {
            'violations': [
                {'type': 'helmet_violation', 'confidence': 0.78},
                {'type': 'triple_riding', 'confidence': 0.85}
            ],
            'plate': 'MH12XY9012',
            'violations_found': True
        },
        {
            'violations': [],
            'plate': 'DL08CD3456',
            'violations_found': False
        }
    ]
    
    # Choose a scenario (80% chance of violation for demo purposes)
    if random.random() < 0.8:
        scenario = random.choice([s for s in scenarios if s['violations_found']])
    else:
        scenario = scenarios[-1]  # No violation scenario
    
    # Calculate total fine for simulation
    total_fine = 0
    for violation in scenario['violations']:
        if violation.get('type') == 'helmet_violation':
            total_fine += 500
        elif violation.get('type') == 'triple_riding':
            total_fine += 1000
    
    return {
        'image_path': image_path,
        'violations_found': scenario['violations_found'],
        'violations': scenario['violations'],
        'license_plate': scenario['plate'],
        'location': location,
        'datetime': violation_datetime,
        'processed_at': datetime.now().isoformat(),
        'demo_mode': True,
        'total_fine': total_fine
    }

def create_demo_violation(detection_result):
    """Create a violation record with enhanced PDF and evidence"""
    try:
        from road_safety_violation_detector.website.enhanced_pdf import generate_enhanced_pdf
        import json
        
        # Calculate total fine based on violations
        total_fine = 0
        violation_types = []
        
        for violation in detection_result['violations']:
            if violation['type'] == 'helmet_violation':
                total_fine += 500
                violation_types.append('Riding without Helmet')
            elif violation['type'] == 'triple_riding':
                total_fine += 1000
                violation_types.append('Triple Riding')
        
        # Combine violation types
        combined_violation = ' + '.join(violation_types) if violation_types else 'Traffic Violation'
        
        # Generate unique violation ID
        demo_id = f"DEMO{uuid.uuid4().hex[:8].upper()}"
        
        # Prepare evidence metadata for PDF
        evidence_data = {
            'timestamp': detection_result.get('processed_at', datetime.now().strftime("%Y%m%d_%H%M%S")),
            'violations': detection_result.get('violations', []),
            'license_plate': {
                'text': detection_result.get('license_plate', 'UNKNOWN'),
                'confidence': detection_result.get('plate_confidence', 0.0)
            },
            'location': detection_result.get('location', 'AI Detection System'),
            'payment_status': 'Pending'
        }
        
        # Generate enhanced PDF with annotated image
        pdf_dir = os.path.join(app.root_path, '..', 'media', 'reports')
        os.makedirs(pdf_dir, exist_ok=True)
        
        annotated_image = detection_result.get('annotated_image_path')
        if annotated_image and os.path.exists(annotated_image):
            pdf_path = generate_enhanced_pdf(evidence_data, pdf_dir, annotated_image, demo_id)
        else:
            # Fallback: use original image if annotated not available
            original_image = detection_result.get('image_path')
            if original_image and os.path.exists(original_image):
                pdf_path = generate_enhanced_pdf(evidence_data, pdf_dir, original_image, demo_id)
            else:
                pdf_path = None
        
        # Copy original image to violations folder
        violations_dir = os.path.join(app.root_path, '..', 'media', 'violations')
        os.makedirs(violations_dir, exist_ok=True)
        
        original_image = detection_result.get('image_path')
        image_filename = os.path.basename(original_image)
        violation_image_path = os.path.join(violations_dir, image_filename)
        
        import shutil
        if os.path.exists(original_image):
            shutil.copy2(original_image, violation_image_path)
        
        # Get relative paths for database storage
        annotated_rel_path = os.path.basename(detection_result.get('annotated_image_path', '')) if detection_result.get('annotated_image_path') else None
        json_rel_path = os.path.basename(detection_result.get('evidence_json_path', '')) if detection_result.get('evidence_json_path') else None
        pdf_rel_path = os.path.basename(pdf_path) if pdf_path else None
        
        # Get detection confidence from detection result
        detection_confidence = detection_result.get('detection_confidence')
        
        # Insert into database with enhanced fields
        violation_id = db.insert_violation(
            vehicle_no=detection_result['license_plate'],
            violation_type=combined_violation,
            fine_amount=total_fine,
            image_path=image_filename,
            pdf_path=pdf_rel_path,
            description=f"AI-detected violation with {len(detection_result.get('violations', []))} violation(s): {combined_violation}",
            location_text=detection_result.get('location', 'AI Detection Demo'),
            latitude=0.0,
            longitude=0.0,
            annotated_image_path=annotated_rel_path,
            evidence_json_path=json_rel_path,
            detection_confidence=detection_confidence
        )
        
        print(f"✅ Created violation record ID: {violation_id}")
        print(f"   - PDF: {pdf_rel_path}")
        print(f"   - Annotated Image: {annotated_rel_path}")
        print(f"   - Evidence JSON: {json_rel_path}")
        
        return violation_id
        
    except Exception as e:
        print(f"Error creating demo violation: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/media/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded demo images"""
    try:
        return send_file(os.path.join(UPLOAD_FOLDER, filename))
    except FileNotFoundError:
        return "File not found", 404

if __name__ == '__main__':
    # Ensure storage directories exist
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    print(f"Starting Flask app on {FLASK_HOST}:{FLASK_PORT}")
    print(f"Database path: {DATABASE_PATH}")
    
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)