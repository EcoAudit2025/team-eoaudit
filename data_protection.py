"""
Data Protection Module for EcoAudit
Ensures user data is saved permanently until creator reset
"""

import os
import shutil
from datetime import datetime
import database as db

class DataProtectionManager:
    """Manages data protection and backup strategies"""
    
    def __init__(self):
        self.backup_dir = "data/backups"
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Ensure backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def create_automatic_backup(self):
        """Create automatic backup of database"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{self.backup_dir}/ecoaudit_backup_{timestamp}.db"
            
            # Copy current database
            if os.path.exists("data/ecoaudit.db"):
                shutil.copy2("data/ecoaudit.db", backup_file)
                return True, f"Backup created: {backup_file}"
            else:
                return False, "No database file found to backup"
        except Exception as e:
            return False, f"Backup failed: {str(e)}"
    
    def get_backup_status(self):
        """Get information about existing backups"""
        if not os.path.exists(self.backup_dir):
            return {"backups": 0, "latest": None}
        
        backups = [f for f in os.listdir(self.backup_dir) if f.endswith('.db')]
        backups.sort(reverse=True)
        
        return {
            "backups": len(backups),
            "latest": backups[0] if backups else None,
            "all_backups": backups
        }
    
    def verify_data_integrity(self):
        """Verify database integrity and user data safety"""
        try:
            session = db.get_session()
            
            # Count total users
            total_users = session.query(db.User).count()
            
            # Count total usage records
            total_usage = session.query(db.UtilityUsage).count()
            
            # Count total recycling records
            total_recycling = session.query(db.RecyclingVerification).count()
            
            session.close()
            
            return {
                "status": "protected",
                "total_users": total_users,
                "total_usage_records": total_usage,
                "total_recycling_records": total_recycling,
                "last_check": datetime.now().isoformat(),
                "protection_active": True
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "protection_active": True
            }

def check_reset_authorization(reset_code):
    """Check if reset code is valid for application reset"""
    VALID_RESET_CODE = "Atishay,Akshaj,Adit@EcoAudit_Team"
    return reset_code == VALID_RESET_CODE

def safe_reset_with_backup(reset_code):
    """Safely reset application with automatic backup"""
    # Create backup before reset
    protection_manager = DataProtectionManager()
    backup_result, backup_message = protection_manager.create_automatic_backup()
    
    if not backup_result:
        return False, f"Reset cancelled - backup failed: {backup_message}"
    
    # Proceed with reset if backup successful
    reset_result, reset_message = db.reset_entire_application(reset_code)
    
    if reset_result:
        return True, f"Reset successful! {reset_message} Backup saved: {backup_message}"
    else:
        return False, f"Reset failed: {reset_message}"

# Initialize protection on import
protection_manager = DataProtectionManager()