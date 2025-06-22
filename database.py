import os
import sqlite3
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, ForeignKey, update, UniqueConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session as SQLAlchemySession
from datetime import datetime, timedelta
import pytz

# Create the database directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Create a SQLite database
DATABASE_URL = 'sqlite:///data/ecoaudit.db'
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define the database models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)  # Removed unique constraint
    email = Column(String(100))  # Removed unique constraint to allow same email for both accounts
    location_type = Column(String(100))  # Urban, Suburban, Rural, etc.
    climate_zone = Column(String(100))   # Tropical, Temperate, etc.
    adults = Column(Integer, default=1)
    children = Column(Integer, default=0)
    seniors = Column(Integer, default=0)
    household_type = Column(String(100))  # Single Person, Family, etc.
    housing_type = Column(String(100))    # Apartment, House, etc.
    energy_features = Column(Text)        # JSON string of features
    household_size = Column(Integer, default=1)  # Total people
    created_at = Column(DateTime, default=datetime.now)
    is_public = Column(String(10), default='private')  # 'public' or 'private'
    environmental_class = Column(String(1))  # A, B, or C
    ai_analysis = Column(Text)
    language = Column(String(50), default='English')  # User's preferred language
    total_points = Column(Integer, default=0)  # Total points earned
    daily_usage_count = Column(Integer, default=0)  # Daily utility usage count
    last_usage_date = Column(DateTime)  # Last utility usage date
    confirmation_code = Column(String(10))  # Private 5-10 digit confirmation code for security
    
    # Relationship to utility usage
    utility_records = relationship("UtilityUsage", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', account_type='{self.is_public}', type='{self.household_type}', class='{self.environmental_class}')>"
    
    # Add a unique constraint for username + is_public combination
    __table_args__ = (
        UniqueConstraint('username', 'is_public', name='unique_username_account_type'),
    )

class UtilityUsage(Base):
    __tablename__ = 'utility_usage'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    water_gallons = Column(Float)
    electricity_kwh = Column(Float)
    gas_cubic_m = Column(Float)
    water_status = Column(String(20))
    electricity_status = Column(String(20))
    gas_status = Column(String(20))
    efficiency_score = Column(Float)
    carbon_footprint = Column(Float)
    points_earned = Column(Integer, default=0)
    
    # Relationship to user
    user = relationship("User", back_populates="utility_records")
    
    def __repr__(self):
        return f"<UtilityUsage(user_id='{self.user_id}', timestamp='{self.timestamp}', water='{self.water_gallons}', electricity='{self.electricity_kwh}', gas='{self.gas_cubic_m}')>"

class Material(Base):
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    reuse_tip = Column(Text)
    recycle_tip = Column(Text)
    search_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Material(name='{self.name}', search_count='{self.search_count}')>"

class RecyclingVerification(Base):
    __tablename__ = 'recycling_verifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    material_name = Column(String(100), nullable=False)
    image_description = Column(Text)  # Store basic image analysis
    verification_status = Column(String(20), default='verified')  # verified, rejected
    points_awarded = Column(Integer, default=3)
    timestamp = Column(DateTime, default=datetime.now)
    
    user = relationship("User", backref="recycling_verifications")
    
    def __repr__(self):
        return f"<RecyclingVerification(user_id='{self.user_id}', material='{self.material_name}', points='{self.points_awarded}')>"

# Create all tables in the database (only if they don't exist)
Base.metadata.create_all(engine)

# Create a session factory
Session = sessionmaker(bind=engine)

def get_session():
    """Get a new database session"""
    return Session()

# Create a global session for backwards compatibility
session: SQLAlchemySession = Session()

# User management functions
def create_user(username, email=None, location_type=None, climate_zone=None, 
                adults=1, children=0, seniors=0, household_type=None, 
                housing_type=None, energy_features=None, is_public='private', language='English', confirmation_code=None):
    """Create a new user with detailed household information"""
    try:
        import json
        
        # Check if user already exists with the same username AND visibility type
        existing_user = session.query(User).filter(
            User.username == username, 
            User.is_public == is_public
        ).first()
        if existing_user:
            return None
        
        household_size = adults + children + seniors
        
        user = User(
            username=username,
            email=email,
            location_type=location_type,
            climate_zone=climate_zone,
            adults=adults,
            children=children,
            seniors=seniors,
            household_type=household_type,
            housing_type=housing_type,
            energy_features=json.dumps(energy_features) if energy_features else None,
            household_size=household_size,
            is_public=is_public,
            language=language,
            confirmation_code=confirmation_code
        )
        session.add(user)
        session.commit()
        session.refresh(user)  # Refresh to get the updated object
        return user
    except Exception as e:
        session.rollback()
        print(f"Error creating user: {e}")
        return None

def get_user(username, is_public=None):
    """Get user by username and optionally by account type"""
    if is_public is not None:
        return session.query(User).filter(
            User.username == username, 
            User.is_public == is_public
        ).first()
    else:
        # Return first match if account type not specified (backward compatibility)
        return session.query(User).filter(User.username == username).first()

def authenticate_user(username, confirmation_code, is_public=None):
    """Authenticate user with username and confirmation code"""
    try:
        if is_public is not None:
            user = session.query(User).filter(
                User.username == username,
                User.is_public == is_public,
                User.confirmation_code == confirmation_code
            ).first()
        else:
            user = session.query(User).filter(
                User.username == username,
                User.confirmation_code == confirmation_code
            ).first()
        return user
    except Exception as e:
        print(f"Authentication error: {e}")
        return None

def validate_confirmation_code(code):
    """Validate confirmation code format (5-10 digits)"""
    if not code:
        return False, "Confirmation code is required"
    
    if not code.isdigit():
        return False, "Confirmation code must contain only numbers"
    
    if len(code) < 5 or len(code) > 10:
        return False, "Confirmation code must be between 5-10 digits"
    
    return True, "Valid confirmation code"

def update_user_confirmation_code(user_id, new_code):
    """Update user's confirmation code"""
    try:
        is_valid, message = validate_confirmation_code(new_code)
        if not is_valid:
            return False, message
        
        session.query(User).filter(User.id == user_id).update({
            User.confirmation_code: new_code
        })
        session.commit()
        return True, "Confirmation code updated successfully"
    except Exception as e:
        session.rollback()
        return False, f"Error updating confirmation code: {e}"

def update_user_profile(user_id, **kwargs):
    """Update user profile information"""
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Update allowed fields
        allowed_fields = [
            'email', 'location_type', 'climate_zone', 'adults', 'children', 
            'seniors', 'household_type', 'housing_type', 'language', 'is_public'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        # Recalculate household size if family composition changed
        if any(field in kwargs for field in ['adults', 'children', 'seniors']):
            adults = getattr(user, 'adults', 0) or 0
            children = getattr(user, 'children', 0) or 0
            seniors = getattr(user, 'seniors', 0) or 0
            setattr(user, 'household_size', adults + children + seniors)
        
        # Handle energy features JSON
        if 'energy_features' in kwargs:
            import json
            setattr(user, 'energy_features', json.dumps(kwargs['energy_features']) if kwargs['energy_features'] else None)
        
        session.commit()
        session.refresh(user)
        return user
    except Exception as e:
        session.rollback()
        print(f"Error updating user profile: {e}")
        return None

def get_all_users():
    """Get all users"""
    return session.query(User).all()

def get_public_users(search_term=None):
    """Get all users who have made their data public, with optional search"""
    query = session.query(User).filter(User.is_public == 'public')
    
    if search_term:
        search_pattern = f"%{search_term.lower()}%"
        query = query.filter(
            User.username.ilike(search_pattern)
        )
    
    return query.all()

def search_public_users(search_term):
    """Search for public users by username"""
    if not search_term:
        return get_public_users()
    
    search_pattern = f"%{search_term.lower()}%"
    return session.query(User).filter(
        User.is_public == 'public',
        User.username.ilike(search_pattern)
    ).all()

def get_user_accounts(username):
    """Get all accounts (public and private) for a username"""
    return session.query(User).filter(User.username == username).all()

def username_has_both_accounts(username):
    """Check if a username has both public and private accounts"""
    accounts = get_user_accounts(username)
    account_types = [account.is_public for account in accounts]
    return 'public' in account_types and 'private' in account_types

def get_username_account_info(username):
    """Get detailed account information for a username"""
    accounts = get_user_accounts(username)
    if not accounts:
        return None
    
    info = {
        'username': username,
        'has_public': False,
        'has_private': False,
        'public_account': None,
        'private_account': None,
        'total_accounts': len(accounts)
    }
    
    for account in accounts:
        account_type = getattr(account, 'is_public', None)
        if account_type == 'public':
            info['has_public'] = True
            info['public_account'] = account
        elif account_type == 'private':
            info['has_private'] = True
            info['private_account'] = account
    
    return info

def update_user_environmental_class(user_id, env_class, ai_analysis):
    """Update user's environmental class and AI analysis"""
    try:
        session.query(User).filter(User.id == user_id).update({
            User.environmental_class: env_class,
            User.ai_analysis: ai_analysis
        })
        session.commit()
        return session.query(User).filter(User.id == user_id).first()
    except Exception as e:
        session.rollback()
        print(f"Error updating environmental class: {e}")
        return None

def calculate_environmental_class(user_usage_data):
    """Calculate environmental class (A, B, C) based on usage patterns"""
    if not user_usage_data:
        return 'C'
    
    # Calculate averages
    avg_water = sum(record.water_gallons for record in user_usage_data) / len(user_usage_data)
    avg_electricity = sum(record.electricity_kwh for record in user_usage_data) / len(user_usage_data)
    avg_gas = sum(record.gas_cubic_m for record in user_usage_data) / len(user_usage_data)
    
    # Define thresholds based on typical ranges
    # Low usage (Class A - Doing Great)
    water_low = 6000  # gallons/month
    electricity_low = 400  # kWh/month
    gas_low = 60  # cubic meters/month
    
    # Normal/High boundary (Class B/C boundary)
    water_high = 12000  # gallons/month
    electricity_high = 800  # kWh/month
    gas_high = 120  # cubic meters/month
    
    # Count how many utilities are in each category
    low_count = 0
    normal_count = 0
    high_count = 0
    
    # Water classification
    if avg_water <= water_low:
        low_count += 1
    elif avg_water <= water_high:
        normal_count += 1
    else:
        high_count += 1
    
    # Electricity classification
    if avg_electricity <= electricity_low:
        low_count += 1
    elif avg_electricity <= electricity_high:
        normal_count += 1
    else:
        high_count += 1
    
    # Gas classification
    if avg_gas <= gas_low:
        low_count += 1
    elif avg_gas <= gas_high:
        normal_count += 1
    else:
        high_count += 1
    
    # Determine class based on usage patterns
    if low_count >= 2:  # At least 2 utilities in low range
        return 'A'  # Doing Great - lots of low usage
    elif high_count >= 2:  # At least 2 utilities in high range
        return 'C'  # Can Work Over - high usage
    else:
        return 'B'  # Doing Just Fine - mostly normal ranges

def generate_user_ai_analysis(user, usage_data):
    """Generate intelligent AI analysis based on actual utility values, usage patterns, and energy features"""
    if not usage_data:
        return "Start tracking your utility usage to receive personalized AI insights based on your household profile and energy features."
    
    # Calculate comprehensive statistics
    avg_water = sum(record.water_gallons for record in usage_data) / len(usage_data)
    avg_electricity = sum(record.electricity_kwh for record in usage_data) / len(usage_data)
    avg_gas = sum(record.gas_cubic_m for record in usage_data) / len(usage_data)
    
    # Calculate trends if multiple data points
    latest_water = usage_data[0].water_gallons if usage_data else 0
    latest_electricity = usage_data[0].electricity_kwh if usage_data else 0
    latest_gas = usage_data[0].gas_cubic_m if usage_data else 0
    
    # Get user context with robust defaults
    household_size = getattr(user, 'household_size', 1) or 1
    adults = getattr(user, 'adults', 1) or 1
    children = getattr(user, 'children', 0) or 0
    seniors = getattr(user, 'seniors', 0) or 0
    location_type = getattr(user, 'location_type', 'Unknown') or 'Unknown'
    housing_type = getattr(user, 'housing_type', 'Unknown') or 'Unknown'
    climate_zone = getattr(user, 'climate_zone', 'Unknown') or 'Unknown'
    
    # Parse energy features
    energy_features = []
    try:
        import json
        energy_features_raw = getattr(user, 'energy_features', '[]') or '[]'
        energy_features = json.loads(energy_features_raw) if energy_features_raw else []
    except:
        energy_features = []
    
    # Calculate per-person usage for context
    water_per_person = avg_water / household_size
    electricity_per_person = avg_electricity / household_size
    gas_per_person = avg_gas / household_size
    
    # Calculate trends
    trend_analysis = ""
    if len(usage_data) > 1:
        water_trend = "stable"
        electricity_trend = "stable"
        gas_trend = "stable"
        
        if len(usage_data) >= 3:
            recent_avg_water = sum(record.water_gallons for record in usage_data[:2]) / 2
            older_avg_water = sum(record.water_gallons for record in usage_data[-2:]) / 2
            
            recent_avg_electricity = sum(record.electricity_kwh for record in usage_data[:2]) / 2
            older_avg_electricity = sum(record.electricity_kwh for record in usage_data[-2:]) / 2
            
            recent_avg_gas = sum(record.gas_cubic_m for record in usage_data[:2]) / 2
            older_avg_gas = sum(record.gas_cubic_m for record in usage_data[-2:]) / 2
            
            if recent_avg_water > older_avg_water * 1.1:
                water_trend = "increasing"
            elif recent_avg_water < older_avg_water * 0.9:
                water_trend = "decreasing"
                
            if recent_avg_electricity > older_avg_electricity * 1.1:
                electricity_trend = "increasing"
            elif recent_avg_electricity < older_avg_electricity * 0.9:
                electricity_trend = "decreasing"
                
            if recent_avg_gas > older_avg_gas * 1.1:
                gas_trend = "increasing"
            elif recent_avg_gas < older_avg_gas * 0.9:
                gas_trend = "decreasing"
        
        trend_analysis = f" Your water usage is {water_trend}, electricity {electricity_trend}, and gas usage {gas_trend} over recent periods."
    
    # Get environmental class
    env_class = calculate_environmental_class(usage_data)
    
    # Generate intelligent analysis based on all factors
    analysis_parts = []
    
    # Household context analysis
    context_analysis = f"Based on your {household_size}-person household ({adults} adults"
    if children > 0:
        context_analysis += f", {children} children"
    if seniors > 0:
        context_analysis += f", {seniors} seniors"
    context_analysis += f") in a {housing_type.lower()} in {location_type.replace(' - ', ' ')}"
    if climate_zone != 'Unknown':
        context_analysis += f" with {climate_zone.lower()} climate"
    context_analysis += ":"
    analysis_parts.append(context_analysis)
    
    # Energy features impact analysis
    if energy_features:
        features_impact = f"Your energy efficiency features ({', '.join(energy_features)}) should provide significant benefits. "
        
        # Analyze if usage aligns with features
        expected_savings = 0
        feature_analysis = []
        
        for feature in energy_features:
            if "LED" in feature or "led" in feature.lower():
                expected_savings += 15
                feature_analysis.append("LED lighting reduces electricity by 75%")
            elif "Smart Thermostat" in feature or "thermostat" in feature.lower():
                expected_savings += 12
                feature_analysis.append("Smart thermostat saves 10-23% on heating/cooling")
            elif "Energy Star" in feature or "energy star" in feature.lower():
                expected_savings += 10
                feature_analysis.append("Energy Star appliances use 10-50% less energy")
            elif "Solar" in feature or "solar" in feature.lower():
                expected_savings += 25
                feature_analysis.append("Solar panels significantly reduce grid electricity")
            elif "Insulation" in feature or "insulation" in feature.lower():
                expected_savings += 20
                feature_analysis.append("Proper insulation reduces heating/cooling by 15%")
        
        features_impact += " ".join(feature_analysis)
        if expected_savings > 0:
            # Compare actual usage to expected efficiency
            baseline_electricity = 600 * (household_size * 0.8)  # Adjust baseline for household size
            expected_usage = baseline_electricity * (1 - expected_savings/100)
            if avg_electricity <= expected_usage * 1.1:
                features_impact += f" Your {avg_electricity:.0f} kWh usage reflects excellent utilization of these features."
            else:
                features_impact += f" Your {avg_electricity:.0f} kWh usage suggests room for optimization despite these features."
        
        analysis_parts.append(features_impact)
    else:
        analysis_parts.append("Consider adding energy-efficient features like LED lighting, smart thermostats, or Energy Star appliances to reduce consumption.")
    
    # Per-person usage analysis with household context
    usage_analysis = f"Per-person consumption: {water_per_person:.0f} gal water, {electricity_per_person:.0f} kWh electricity, {gas_per_person:.0f} m³ gas."
    
    # Contextual benchmarks based on household type
    if "Family" in getattr(user, 'household_type', ''):
        if children > 0:
            usage_analysis += " Families with children typically use 20-30% more utilities due to increased activity and longer home occupancy."
        if "Teenagers" in getattr(user, 'household_type', ''):
            usage_analysis += " Teenage children often increase electricity usage significantly due to electronics and extended shower times."
    elif "Senior" in getattr(user, 'household_type', ''):
        usage_analysis += " Senior households often have higher heating costs but lower overall consumption due to fixed schedules."
    
    analysis_parts.append(usage_analysis)
    
    # Environmental class with detailed reasoning
    if env_class == 'A':
        analysis_parts.append(f"Exceptional environmental performance! Your {household_size}-person household in {location_type} area achieves outstanding sustainability levels.")
    elif env_class == 'B':
        analysis_parts.append(f"Good environmental awareness shown by your {household_size}-person household. Strategic improvements could elevate your sustainability impact.")
    else:
        analysis_parts.append(f"Significant opportunity for your {household_size}-person household to reduce environmental impact through targeted conservation efforts.")
    
    # Intelligent water analysis with specific values
    if avg_water > 300:
        analysis_parts.append(f"Water usage at {avg_water:.0f} gallons/month ({water_per_person:.0f} per person) is significantly above sustainable levels. Immediate action recommended: install low-flow fixtures, fix leaks, reduce shower time to 5 minutes.")
    elif avg_water > 200:
        analysis_parts.append(f"Water consumption at {avg_water:.0f} gallons/month needs improvement. Target reduction to under 150 gallons through efficient appliances and conservation habits.")
    elif avg_water > 100:
        analysis_parts.append(f"Water usage at {avg_water:.0f} gallons/month is moderate. Small improvements like shorter showers could achieve excellent levels under 100 gallons.")
    elif avg_water > 50:
        analysis_parts.append(f"Good water efficiency at {avg_water:.0f} gallons/month. You're approaching excellent conservation levels - continue current practices.")
    else:
        analysis_parts.append(f"Outstanding water conservation at {avg_water:.0f} gallons/month! You're setting an example for sustainable water use.")
    
    # Intelligent electricity analysis with specific values
    if avg_electricity > 1000:
        analysis_parts.append(f"Electricity usage at {avg_electricity:.0f} kWh/month ({electricity_per_person:.0f} per person) requires immediate attention. Priority actions: LED lighting, programmable thermostat, energy-efficient appliances.")
    elif avg_electricity > 800:
        analysis_parts.append(f"Electricity consumption at {avg_electricity:.0f} kWh/month is above sustainable levels. Focus on heating/cooling efficiency and phantom load elimination.")
    elif avg_electricity > 600:
        analysis_parts.append(f"Electricity usage at {avg_electricity:.0f} kWh/month shows room for improvement. Target under 400 kWh through smart energy management.")
    elif avg_electricity > 400:
        analysis_parts.append(f"Moderate electricity consumption at {avg_electricity:.0f} kWh/month. Fine-tuning usage patterns could achieve excellent efficiency.")
    elif avg_electricity > 200:
        analysis_parts.append(f"Good energy efficiency at {avg_electricity:.0f} kWh/month. You're approaching exemplary conservation levels.")
    else:
        analysis_parts.append(f"Exceptional energy efficiency at {avg_electricity:.0f} kWh/month! Your household demonstrates outstanding electrical conservation.")
    
    # Intelligent gas analysis with specific values
    if avg_gas > 120:
        analysis_parts.append(f"Gas consumption at {avg_gas:.0f} m³/month ({gas_per_person:.0f} per person) is high. Consider insulation improvements, efficient heating systems, and temperature management.")
    elif avg_gas > 80:
        analysis_parts.append(f"Gas usage at {avg_gas:.0f} m³/month needs optimization. Focus on heating efficiency and cooking practices to reduce consumption.")
    elif avg_gas > 60:
        analysis_parts.append(f"Gas consumption at {avg_gas:.0f} m³/month is moderate. Small adjustments in heating habits could improve efficiency.")
    elif avg_gas > 40:
        analysis_parts.append(f"Good gas efficiency at {avg_gas:.0f} m³/month. You're managing heating and cooking consumption well.")
    elif avg_gas > 20:
        analysis_parts.append(f"Excellent gas conservation at {avg_gas:.0f} m³/month. Your heating and cooking practices are highly efficient.")
    else:
        analysis_parts.append(f"Outstanding gas efficiency at {avg_gas:.0f} m³/month! Minimal gas consumption demonstrates excellent conservation.")
    
    # Calculate estimated carbon footprint
    carbon_water = avg_water * 0.002  # kg CO2 per gallon
    carbon_electricity = avg_electricity * 0.4  # kg CO2 per kWh (US average)
    carbon_gas = avg_gas * 2.2  # kg CO2 per m³
    total_carbon = carbon_water + carbon_electricity + carbon_gas
    
    # Add carbon footprint insight
    if total_carbon > 500:
        analysis_parts.append(f"Your estimated monthly carbon footprint is {total_carbon:.0f} kg CO2 - focus on your highest usage areas for maximum impact.")
    elif total_carbon > 300:
        analysis_parts.append(f"Monthly carbon footprint of {total_carbon:.0f} kg CO2 is moderate - targeted improvements could significantly reduce your impact.")
    else:
        analysis_parts.append(f"Excellent carbon efficiency with {total_carbon:.0f} kg CO2 monthly footprint. You're contributing positively to climate goals.")
    
    # Add contextual recommendations based on housing type
    if housing_type and housing_type != 'Unknown':
        if housing_type.lower() in ['apartment', 'condo']:
            analysis_parts.append("As an apartment/condo resident, focus on efficient appliances, LED lighting, and smart heating/cooling management.")
        elif housing_type.lower() in ['house', 'single family']:
            analysis_parts.append("For your house, consider insulation upgrades, programmable thermostats, and potentially renewable energy options.")
    
    # Add seasonal or trend insights if multiple records
    if len(usage_data) > 1:
        recent_avg = sum(record.electricity_kwh for record in usage_data[:3]) / min(3, len(usage_data))
        older_avg = sum(record.electricity_kwh for record in usage_data[-3:]) / min(3, len(usage_data))
        
        if recent_avg < older_avg * 0.9:
            analysis_parts.append("Positive trend detected - your recent usage shows improving efficiency!")
        elif recent_avg > older_avg * 1.1:
            analysis_parts.append("Usage has increased recently - review recent changes in habits or appliances.")
    
    return " ".join(analysis_parts)
    
    # Household adjustment
    household_note = f"Analysis adjusted for household size of {user.household_size} people."
    analysis_parts.append(household_note)
    
    return " ".join(analysis_parts)

def check_daily_usage_limit(user_id):
    """Check if user has reached daily usage limit (2 entries per day) - Using Indian Standard Time"""
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        
        # Use Indian Standard Time (IST)
        ist = pytz.timezone('Asia/Kolkata')
        current_time_utc = datetime.now(pytz.UTC)
        current_time_ist = current_time_utc.astimezone(ist)
        today_ist = current_time_ist.date()
        
        # Check if we need to reset the daily count based on IST
        should_reset = False
        if not user.last_usage_date:
            should_reset = True
        else:
            # Convert stored UTC time to IST for comparison
            last_usage_ist = user.last_usage_date.replace(tzinfo=pytz.UTC).astimezone(ist)
            if last_usage_ist.date() < today_ist:
                should_reset = True
        
        if should_reset:
            user.daily_usage_count = 0
            user.last_usage_date = current_time_utc.replace(tzinfo=None)  # Store as UTC
            session.commit()
        
        # Count actual usage entries for today (IST) to verify limit
        today_usage_count = session.query(func.count(UtilityUsage.id)).filter(
            UtilityUsage.user_id == user_id,
            func.date(UtilityUsage.timestamp) == today_ist
        ).scalar() or 0
        
        # Update user's count to match actual database entries
        if user.daily_usage_count != today_usage_count:
            user.daily_usage_count = today_usage_count
            session.commit()
        
        # Check if limit reached
        if user.daily_usage_count >= 2:
            # Get the most recent 2 usage entries to calculate 24-hour window
            recent_entries = session.query(UtilityUsage).filter(
                UtilityUsage.user_id == user_id
            ).order_by(UtilityUsage.timestamp.desc()).limit(2).all()
            
            if len(recent_entries) >= 2:
                # Get the second most recent entry (24-hour window starts from here)
                second_recent_entry = recent_entries[1]
                entry_time = second_recent_entry.timestamp
                
                # Convert to UTC if needed
                if entry_time.tzinfo is None:
                    entry_time = pytz.UTC.localize(entry_time)
                
                # Calculate 24 hours from the second entry
                next_available_time = entry_time + timedelta(hours=24)
                current_time_utc = datetime.now(pytz.UTC)
                
                # Check if 24 hours have passed
                if current_time_utc >= next_available_time:
                    # 24 hours have passed, reset count and allow entry
                    user.daily_usage_count = 1  # Will become 2 after this entry
                    session.commit()
                    return True, "24-hour window expired. You can now save new entries."
                else:
                    # Calculate remaining time in 24-hour window
                    time_until_available = next_available_time - current_time_utc
                    hours_left = int(time_until_available.total_seconds() // 3600)
                    minutes_left = int((time_until_available.total_seconds() % 3600) // 60)
                    
                    return False, f"Daily limit reached (2/2 entries used). Next entry available in {hours_left}h {minutes_left}m (24-hour timer)"
            else:
                # Fallback to IST midnight reset if we don't have enough entries
                tomorrow_ist = datetime.combine(today_ist + timedelta(days=1), datetime.min.time())
                tomorrow_ist = ist.localize(tomorrow_ist)
                time_until_reset = tomorrow_ist - current_time_ist
                hours_left = int(time_until_reset.total_seconds() // 3600)
                minutes_left = int((time_until_reset.total_seconds() % 3600) // 60)
                
                return False, f"Daily limit reached (2/2 entries used). Next entry available in {hours_left}h {minutes_left}m"
        
        entries_left = 2 - user.daily_usage_count
        return True, f"You can save {entries_left} more entries today (IST timezone)"
        
    except Exception as e:
        session.rollback()
        return False, f"Error checking usage limit: {e}"
    finally:
        session.close()

def get_time_until_reset(user_id):
    """Get time remaining until daily usage limit resets"""
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user or not user.last_usage_date:
            return "00:00:00"
        
        today = datetime.now().date()
        if user.last_usage_date.date() != today:
            return "00:00:00"  # Already reset
        
        from datetime import timedelta
        tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
        time_until_reset = tomorrow - datetime.now()
        
        hours = int(time_until_reset.total_seconds() // 3600)
        minutes = int((time_until_reset.total_seconds() % 3600) // 60)
        seconds = int(time_until_reset.total_seconds() % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    except Exception as e:
        return "00:00:00"
    finally:
        session.close()

def save_utility_usage(user_id, water_gallons, electricity_kwh, gas_cubic_m, water_status, electricity_status, gas_status, efficiency_score=None, carbon_footprint=None, ai_points=None):
    """Save utility usage data to the database for a specific user with daily limit check and AI-based points"""
    session = get_session()
    try:
        # Check daily usage limit first
        can_save, message = check_daily_usage_limit(user_id)
        if not can_save:
            return False, message
        
        # Use AI points if provided, otherwise calculate traditional points
        if ai_points is not None:
            points_earned = int(ai_points)  # Convert AI points (0-10) to integer for storage
        else:
            points_earned = calculate_sustainability_points(water_gallons, electricity_kwh, gas_cubic_m)
        
        usage = UtilityUsage(
            user_id=user_id,
            water_gallons=water_gallons,
            electricity_kwh=electricity_kwh,
            gas_cubic_m=gas_cubic_m,
            water_status=water_status,
            electricity_status=electricity_status,
            gas_status=gas_status,
            efficiency_score=efficiency_score,
            carbon_footprint=carbon_footprint,
            points_earned=points_earned
        )
        session.add(usage)
        
        # Update user's daily usage count and last usage date
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.daily_usage_count += 1
            user.last_usage_date = datetime.now()
            
            # Update user's total points (only for public users)
            if user.is_public == 'public':
                current_points = user.total_points if user.total_points is not None else 0
                user.total_points = current_points + points_earned
        
        session.commit()
        
        # Update environmental classification after saving usage data
        if user:
            # Get all usage data for this user
            user_usage_data = session.query(UtilityUsage).filter(UtilityUsage.user_id == user_id).all()
            
            # Calculate new environmental class
            new_env_class = calculate_environmental_class(user_usage_data)
            
            # Generate AI analysis
            ai_analysis = generate_user_ai_analysis(user, user_usage_data)
            
            # Update user's environmental class and analysis
            update_user_environmental_class(user_id, new_env_class, ai_analysis)
        
        entries_left = 2 - user.daily_usage_count if user else 0
        return True, f"Data saved successfully! You have {entries_left} entries left today."
        
    except Exception as e:
        session.rollback()
        return False, f"Error saving data: {e}"
    finally:
        session.close()

def get_utility_history(user_id=None, limit=10):
    """Get utility usage history from the database"""
    if user_id:
        return session.query(UtilityUsage).filter(UtilityUsage.user_id == user_id).order_by(UtilityUsage.timestamp.desc()).limit(limit).all()
    else:
        return session.query(UtilityUsage).order_by(UtilityUsage.timestamp.desc()).limit(limit).all()

def get_user_usage_last_year(user_id):
    """Get all usage data for a user from the last year"""
    from datetime import datetime, timedelta
    one_year_ago = datetime.now() - timedelta(days=365)
    return session.query(UtilityUsage).filter(
        UtilityUsage.user_id == user_id,
        UtilityUsage.timestamp >= one_year_ago
    ).order_by(UtilityUsage.timestamp.desc()).all()

# Initialize the database with material data and test user
def initialize_materials():
    materials_data = [
        {
            "name": "plastic bag",
            "reuse_tip": "Use as trash liners or for storage.",
            "recycle_tip": "Drop at a plastic bag collection center."
        },
        {
            "name": "plastic bottle",
            "reuse_tip": "Make a bird feeder or pen stand.",
            "recycle_tip": "Rinse and recycle if marked recyclable (1 or 2)."
        },
        {
            "name": "plastic container",
            "reuse_tip": "Store food or small items.",
            "recycle_tip": "Recycle if labeled properly."
        },
        {
            "name": "glass",
            "reuse_tip": "Use glass jars for storage.",
            "recycle_tip": "Clean and recycle in glass bin."
        },
        {
            "name": "phone",
            "reuse_tip": "Repurpose or sell old electronics.",
            "recycle_tip": "Drop at electronic stores or recycling centers."
        },
        {
            "name": "metal",
            "reuse_tip": "Use cans for crafts or storage.",
            "recycle_tip": "Recycle in metal bin."
        },
        {
            "name": "e-waste",
            "reuse_tip": "Old devices can be reused for learning.",
            "recycle_tip": "Certified e-waste recycling centers accept these."
        },
        {
            "name": "styrofoam",
            "reuse_tip": "Reuse for packaging or crafts.",
            "recycle_tip": "Difficult to recycle, avoid use if possible."
        },
    ]
    
    # Check if materials already exist
    existing_materials = session.query(Material).count()
    if existing_materials == 0:
        for material_data in materials_data:
            material = Material(
                name=material_data["name"],
                reuse_tip=material_data["reuse_tip"],
                recycle_tip=material_data["recycle_tip"],
                search_count=0
            )
            session.add(material)
        
        session.commit()
        print("Database initialized with material data")
        
    # No default test user - app starts completely fresh

# Database helper functions for backward compatibility
def save_utility_usage_legacy(water_gallons, electricity_kwh, gas_cubic_m, water_status, electricity_status, gas_status):
    """Legacy function for backward compatibility - creates default user if needed"""
    # Get or create default user
    default_user = session.query(User).filter(User.username == 'default_user').first()
    if not default_user:
        default_user = User(
            username='default_user',
            email='default@ecoaudit.com',
            location='Unknown',
            household_size=1,
            is_public='public'
        )
        session.add(default_user)
        session.commit()
    
    return save_utility_usage(
        user_id=default_user.id,
        water_gallons=water_gallons,
        electricity_kwh=electricity_kwh,
        gas_cubic_m=gas_cubic_m,
        water_status=water_status,
        electricity_status=electricity_status,
        gas_status=gas_status
    )

def find_material(material_name):
    # Convert to lowercase for case-insensitive search
    material_name = material_name.lower()
    
    # Try exact match first
    material = session.query(Material).filter(Material.name == material_name).first()
    
    # If no exact match, try partial match
    if not material:
        material = session.query(Material).filter(Material.name.like(f"%{material_name}%")).first()
    
    if material:
        # Increment search count
        material_id = material.id
        session.query(Material).filter(Material.id == material_id).update(
            {Material.search_count: Material.search_count + 1}
        )
        session.commit()
        # Refresh the material object
        material = session.query(Material).filter(Material.id == material_id).first()
        return material
    
    return None

def save_material(material_name, reuse_tip, recycle_tip):
    # Check if material already exists
    material = session.query(Material).filter(Material.name == material_name.lower()).first()
    
    if material:
        # Update existing material
        material_id = material.id
        session.query(Material).filter(Material.id == material_id).update(
            {
                Material.reuse_tip: reuse_tip,
                Material.recycle_tip: recycle_tip,
                Material.search_count: Material.search_count + 1
            }
        )
        session.commit()
        material = session.query(Material).filter(Material.id == material_id).first()
    else:
        # Create new material
        material = Material(
            name=material_name.lower(),
            reuse_tip=reuse_tip,
            recycle_tip=recycle_tip,
            search_count=1
        )
        session.add(material)
        session.commit()
    
    return material

def get_popular_materials(limit=5):
    return session.query(Material).order_by(Material.search_count.desc()).limit(limit).all()

# Ranking system functions
def calculate_sustainability_points(water_gallons, electricity_kwh, gas_cubic_m):
    """Calculate sustainability points based on combined utility usage - maximum 5 points total"""
    # Calculate individual scores (0-100 scale)
    water_score = 0
    electricity_score = 0
    gas_score = 0
    
    # Water usage scoring (corrected thresholds - very low usage should be excellent)
    if water_gallons <= 10:      # 3.5 gallons would be here - Excellent
        water_score = 100
    elif water_gallons <= 25:
        water_score = 90
    elif water_gallons <= 50:
        water_score = 80
    elif water_gallons <= 100:
        water_score = 70
    elif water_gallons <= 150:
        water_score = 60
    elif water_gallons <= 200:
        water_score = 40
    elif water_gallons <= 300:
        water_score = 20
    else:
        water_score = 0
    
    # Electricity usage scoring (lower is better)
    if electricity_kwh <= 200:
        electricity_score = 100   # Excellent
    elif electricity_kwh <= 400:
        electricity_score = 80    # Very Good
    elif electricity_kwh <= 600:
        electricity_score = 60    # Good
    elif electricity_kwh <= 800:
        electricity_score = 40    # Fair
    elif electricity_kwh <= 1000:
        electricity_score = 20    # Poor
    else:
        electricity_score = 0     # Very Poor
    
    # Gas usage scoring (lower is better)
    if gas_cubic_m <= 20:
        gas_score = 100    # Excellent
    elif gas_cubic_m <= 40:
        gas_score = 80     # Very Good
    elif gas_cubic_m <= 60:
        gas_score = 60     # Good
    elif gas_cubic_m <= 80:
        gas_score = 40     # Fair
    elif gas_cubic_m <= 100:
        gas_score = 20     # Poor
    else:
        gas_score = 0      # Very Poor
    
    # Calculate weighted combined score (water 40%, electricity 40%, gas 20%)
    combined_score = (water_score * 0.4) + (electricity_score * 0.4) + (gas_score * 0.2)
    
    # Convert to 1-5 point scale
    if combined_score >= 90:
        return 5    # Outstanding combined performance
    elif combined_score >= 75:
        return 4    # Very good combined performance  
    elif combined_score >= 60:
        return 3    # Good combined performance
    elif combined_score >= 40:
        return 2    # Fair combined performance
    elif combined_score >= 20:
        return 1    # Poor combined performance
    else:
        return 0    # Very poor combined performance

def update_user_points(user_id, points_to_add):
    """Update user's total points"""
    user = session.query(User).filter(User.id == user_id).first()
    if user:
        current_points = user.total_points if user.total_points is not None else 0
        session.query(User).filter(User.id == user_id).update({
            User.total_points: current_points + points_to_add
        })
        session.commit()
        return current_points + points_to_add
    return 0

def get_global_rankings(limit=10):
    """Get top ranking public users by points (handles negative points correctly)"""
    return session.query(User).filter(
        User.is_public == 'public'
    ).order_by(User.total_points.desc().nulls_last()).limit(limit).all()

def get_user_rank(user_id):
    """Get user's current rank among public users (handles negative points correctly)"""
    user = session.query(User).filter(User.id == user_id).first()
    if not user or user.is_public != 'public':
        return None
    
    user_points = user.total_points if user.total_points is not None else 0
    
    # Count users with higher points (including handling of negative points)
    higher_ranked = session.query(User).filter(
        User.is_public == 'public',
        User.total_points > user_points
    ).count()
    
    return higher_ranked + 1

def recalculate_all_user_points():
    """Recalculate points for all public users based on their usage history"""
    public_users = session.query(User).filter(User.is_public == 'public').all()
    
    for user in public_users:
        total_points = 0
        usage_records = session.query(UtilityUsage).filter(UtilityUsage.user_id == user.id).all()
        
        for record in usage_records:
            water_val = record.water_gallons if record.water_gallons is not None else 0
            electricity_val = record.electricity_kwh if record.electricity_kwh is not None else 0
            gas_val = record.gas_cubic_m if record.gas_cubic_m is not None else 0
            
            points = calculate_sustainability_points(water_val, electricity_val, gas_val)
            total_points += points
        
        session.query(User).filter(User.id == user.id).update({
            User.total_points: total_points
        })
    
    session.commit()

def classify_all_users():
    """Classify all users who have usage data but no environmental class"""
    users = session.query(User).all()
    
    for user in users:
        usage_records = session.query(UtilityUsage).filter(UtilityUsage.user_id == user.id).all()
        
        if usage_records:  # Only classify users who have usage data
            # Calculate environmental class
            env_class = calculate_environmental_class(usage_records)
            
            # Generate AI analysis
            ai_analysis = generate_user_ai_analysis(user, usage_records)
            
            # Update user's classification
            update_user_environmental_class(user.id, env_class, ai_analysis)
    
    print(f"Classified {len(users)} users based on their usage data")

def delete_user_account_permanently(user_id):
    """Delete a user account and all associated data permanently"""
    session = get_session()
    try:
        # First, delete all recycling verifications for this user
        session.query(RecyclingVerification).filter(
            RecyclingVerification.user_id == user_id
        ).delete()
        
        # Delete all utility usage records for this user
        session.query(UtilityUsage).filter(
            UtilityUsage.user_id == user_id
        ).delete()
        
        # Finally, delete the user
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            username = user.username
            account_type = user.is_public
            session.delete(user)
            session.commit()
            return True, f"Account '{username}' ({account_type}) and all associated data have been permanently deleted."
        else:
            return False, "User not found."
            
    except Exception as e:
        session.rollback()
        return False, f"Error deleting account: {str(e)}"
    finally:
        session.close()

def reset_entire_application():
    """CREATOR'S ONLY: Reset the entire application - DELETE ALL DATA"""
    try:
        # Delete all recycling verifications
        session.query(RecyclingVerification).delete()
        
        # Delete all utility usage records
        session.query(UtilityUsage).delete()
        
        # Delete all users
        session.query(User).delete()
        
        # Reset material search counts (keep materials but reset counts)
        session.query(Material).update({Material.search_count: 0})
        
        # Commit all deletions
        session.commit()
        
        return True, "Application successfully reset! All users and data have been deleted."
    except Exception as e:
        session.rollback()
        return False, f"Error resetting application: {str(e)}"

# Recycling verification functions
def save_recycling_verification(user_id, material_name, image_description, verification_status='verified', points_awarded=3):
    """Save a recycling verification record"""
    try:
        verification = RecyclingVerification(
            user_id=user_id,
            material_name=material_name,
            image_description=image_description,
            verification_status=verification_status,
            points_awarded=points_awarded
        )
        session.add(verification)
        
        # Update user's total points if verification is successful
        if verification_status == 'verified':
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                current_points = getattr(user, 'total_points', 0) or 0
                setattr(user, 'total_points', current_points + points_awarded)
        
        session.commit()
        session.refresh(verification)
        return verification
    except Exception as e:
        session.rollback()
        print(f"Error saving recycling verification: {e}")
        return None

def get_user_recycling_verifications(user_id, limit=10):
    """Get recycling verification history for a user"""
    return session.query(RecyclingVerification).filter(
        RecyclingVerification.user_id == user_id
    ).order_by(RecyclingVerification.timestamp.desc()).limit(limit).all()

def get_total_recycling_points(user_id):
    """Get total recycling points earned by a user"""
    result = session.query(RecyclingVerification).filter(
        RecyclingVerification.user_id == user_id,
        RecyclingVerification.verification_status == 'verified'
    ).count()
    return result * 3  # 3 points per verified recycling

def basic_image_verification(image_description, material_name):
    """Enhanced image verification with comprehensive feedback for any type of image"""
    # Convert to lowercase for case-insensitive matching
    desc_lower = image_description.lower().strip()
    material_lower = material_name.lower()
    
    # If no description provided, still give feedback
    if not desc_lower:
        return {
            'verified': True,
            'confidence': 'low',
            'reason': 'Thanks for uploading an image! Next time, try describing your recycling activity for better feedback.',
            'feedback': 'We appreciate your environmental effort! Adding a description helps us provide more specific guidance.',
            'points_justification': 'Participation in environmental activities earns points'
        }
    
    # Expanded keywords for better recognition
    recycling_keywords = [
        'recycle', 'recycling', 'bin', 'container', 'disposal', 'waste', 'trash',
        'plastic', 'bottle', 'can', 'paper', 'cardboard', 'glass', 'metal',
        'throwing away', 'putting in', 'sorting', 'separating', 'disposing',
        'compost', 'composting', 'reuse', 'reusing', 'upcycle', 'upcycling',
        'clean', 'cleaning', 'wash', 'washing', 'prepare', 'preparing'
    ]
    
    # Environmental action keywords
    environmental_keywords = [
        'environment', 'environmental', 'green', 'eco', 'sustainable', 'sustainability',
        'save', 'saving', 'reduce', 'reducing', 'help', 'helping', 'earth', 'planet'
    ]
    
    # Check for material mention
    material_match = material_lower in desc_lower
    
    # Check for recycling-related keywords
    recycling_activity = any(keyword in desc_lower for keyword in recycling_keywords)
    
    # Check for environmental awareness
    environmental_awareness = any(keyword in desc_lower for keyword in environmental_keywords)
    
    # Enhanced verification logic with detailed feedback
    if material_match and recycling_activity:
        return {
            'verified': True,
            'confidence': 'high',
            'reason': f'Excellent! You clearly described recycling {material_name} properly.',
            'feedback': f'Great environmental action! Proper {material_name} recycling helps reduce waste and conserve resources.',
            'points_justification': 'High-quality recycling activity with clear material identification'
        }
    elif recycling_activity:
        return {
            'verified': True,
            'confidence': 'medium',
            'reason': 'Good recycling activity detected in your description.',
            'feedback': 'Thank you for your environmental effort! Every recycling action makes a difference.',
            'points_justification': 'Active participation in recycling activities'
        }
    elif environmental_awareness:
        return {
            'verified': True,
            'confidence': 'medium',
            'reason': 'Environmental awareness and positive action detected.',
            'feedback': 'We appreciate your environmental consciousness! Keep up the sustainable practices.',
            'points_justification': 'Demonstrated environmental awareness and sustainable thinking'
        }
    elif material_match:
        return {
            'verified': True,
            'confidence': 'medium',
            'reason': f'You mentioned {material_name} in your activity.',
            'feedback': f'Thanks for focusing on {material_name}! Consider describing the specific recycling action for more detailed guidance.',
            'points_justification': 'Material-focused environmental activity'
        }
    else:
        # Still give points for participation, but with encouraging feedback
        return {
            'verified': True,
            'confidence': 'participation',
            'reason': 'Thank you for participating in our environmental verification system!',
            'feedback': 'Every environmental action counts! Try including words like "recycling", "bin", or "disposal" in your description for more specific feedback.',
            'points_justification': 'Active engagement with environmental sustainability platform'
        }

# Initialize the database with materials
initialize_materials()