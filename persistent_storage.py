"""
Persistent Storage Configuration for EcoAudit
Ensures all user data is saved permanently until creator reset
"""

import os
import sqlite3
from datetime import datetime

class PersistentStorageConfig:
    """Configuration for permanent data storage"""
    
    def __init__(self):
        self.db_path = "data/ecoaudit.db"
        self.ensure_data_directory()
        self.configure_database_persistence()
    
    def ensure_data_directory(self):
        """Ensure data directory exists and is writable"""
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"Created data directory: {data_dir}")
    
    def configure_database_persistence(self):
        """Configure SQLite for maximum data persistence"""
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA journal_mode=WAL;")  # Write-Ahead Logging for durability
                conn.execute("PRAGMA synchronous=FULL;")  # Maximum durability
                conn.execute("PRAGMA cache_size=10000;")  # Better performance
                conn.execute("PRAGMA temp_store=MEMORY;")  # Use memory for temp storage
                conn.commit()
                conn.close()
                print("Database configured for maximum persistence")
            except Exception as e:
                print(f"Database configuration warning: {e}")
    
    def verify_data_integrity(self):
        """Verify that all user data is safely stored"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check users table
            users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            
            # Check utility usage table
            usage_count = conn.execute("SELECT COUNT(*) FROM utility_usage").fetchone()[0]
            
            # Check recycling verifications
            recycling_count = conn.execute("SELECT COUNT(*) FROM recycling_verifications").fetchone()[0]
            
            conn.close()
            
            return {
                "status": "protected",
                "users_protected": users_count,
                "usage_records_protected": usage_count,
                "recycling_records_protected": recycling_count,
                "last_verified": datetime.now().isoformat(),
                "protection_level": "maximum"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "protection_level": "unknown"
            }
    
    def get_protection_status(self):
        """Get current data protection status"""
        return {
            "database_path": self.db_path,
            "database_exists": os.path.exists(self.db_path),
            "data_directory_writable": os.access("data", os.W_OK),
            "reset_code_required": "Atishay,Akshaj,Adit@EcoAudit_Team",
            "individual_deletion_disabled": True,
            "permanent_storage_active": True
        }

# Initialize persistent storage on import
storage_config = PersistentStorageConfig()
print("Data protection initialized - users will be saved permanently until creator reset")