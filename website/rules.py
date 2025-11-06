"""
Fine calculation logic for Road Safety Violation Detector
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from configs.config import FIRST_OFFENSE_FINE, REPEAT_OFFENSE_FINE
from db.models import DatabaseManager

def compute_fine(vehicle_no, violation_type, db):
    """
    Compute fine amount based on violation history
    
    Args:
        vehicle_no (str): Vehicle number
        violation_type (str): Type of violation
        db (DatabaseManager): Database manager instance
    
    Returns:
        int: Fine amount
    """
    # Count previous violations for this vehicle
    previous_violations = db.count_previous_violations(vehicle_no)
    
    # First offense: ₹500, repeat offense: ₹1000
    if previous_violations == 0:
        return FIRST_OFFENSE_FINE
    else:
        return REPEAT_OFFENSE_FINE