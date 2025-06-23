"""
Comprehensive error handling and logging system for EcoAudit
Ensures robust application performance with graceful error recovery
"""

import logging
import traceback
from functools import wraps
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ecoaudit.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def safe_execute(fallback_return=None, log_errors=True):
    """
    Decorator for safe function execution with error handling
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                return fallback_return
        return wrapper
    return decorator

def validate_inputs(water=None, electricity=None, gas=None):
    """
    Validate user inputs for utility usage
    Returns: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    # Check for negative values
    if water is not None and water < 0:
        errors.append("Water usage cannot be negative")
    if electricity is not None and electricity < 0:
        errors.append("Electricity usage cannot be negative")
    if gas is not None and gas < 0:
        errors.append("Gas usage cannot be negative")
    
    # Check for unrealistic values
    if water is not None and water > 50000:
        warnings.append("Water usage seems unusually high")
    if electricity is not None and electricity > 10000:
        warnings.append("Electricity usage seems unusually high")
    if gas is not None and gas > 2000:
        warnings.append("Gas usage seems unusually high")
    
    return len(errors) == 0, errors, warnings

class ErrorRecovery:
    """Handle various application errors with appropriate fallbacks"""
    
    @staticmethod
    def database_error_fallback():
        """Fallback for database connection issues"""
        return {
            'status': 'error',
            'message': 'Database temporarily unavailable. Please try again shortly.',
            'fallback_active': True
        }
    
    @staticmethod
    def ai_error_fallback():
        """Fallback for AI model failures"""
        return {
            'recommendations': [
                "Monitor usage patterns regularly",
                "Implement basic conservation practices",
                "Check for unusual consumption spikes"
            ],
            'efficiency_score': 50.0,
            'status': 'fallback_active'
        }
    
    @staticmethod
    def chatbot_error_fallback(user_input=""):
        """Fallback for chatbot failures"""
        return f"I apologize, but I'm experiencing a temporary issue. I understand you asked about '{user_input}'. Please try rephrasing your question, and I'll do my best to help with environmental guidance and app support."

def log_user_action(action, user_id=None, details=None):
    """Log user actions for debugging and analytics"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'user_id': user_id,
        'details': details
    }
    logger.info(f"User Action: {log_entry}")

def handle_import_errors():
    """Check and handle import errors for optional dependencies"""
    missing_deps = []
    
    try:
        import textdistance
    except ImportError:
        missing_deps.append('textdistance')
    
    try:
        import tensorflow
    except ImportError:
        missing_deps.append('tensorflow')
    
    if missing_deps:
        logger.warning(f"Optional dependencies not available: {missing_deps}")
        logger.info("Application will continue with fallback implementations")
    
    return missing_deps