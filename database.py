import os
import sqlite3
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, ForeignKey, update, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session as SQLAlchemySession
from datetime import datetime

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
                housing_type=None, energy_features=None, is_public='private', language='English'):
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
            language=language
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
    """Generate intelligent AI analysis based on actual utility values and usage patterns"""
    if not usage_data:
        return "Insufficient data for analysis. Start tracking your utility usage to get personalized insights."
    
    # Calculate comprehensive statistics
    avg_water = sum(record.water_gallons for record in usage_data) / len(usage_data)
    avg_electricity = sum(record.electricity_kwh for record in usage_data) / len(usage_data)
    avg_gas = sum(record.gas_cubic_m for record in usage_data) / len(usage_data)
    
    # Calculate trends if multiple data points
    latest_water = usage_data[0].water_gallons if usage_data else 0
    latest_electricity = usage_data[0].electricity_kwh if usage_data else 0
    latest_gas = usage_data[0].gas_cubic_m if usage_data else 0
    
    # Get user context
    household_size = getattr(user, 'household_size', 1) or 1
    location_type = getattr(user, 'location_type', 'Unknown') or 'Unknown'
    housing_type = getattr(user, 'housing_type', 'Unknown') or 'Unknown'
    
    # Calculate per-person usage for context
    water_per_person = avg_water / household_size
    electricity_per_person = avg_electricity / household_size
    gas_per_person = avg_gas / household_size
    
    # Get environmental class
    env_class = calculate_environmental_class(usage_data)
    
    # Generate intelligent analysis
    analysis_parts = []
    
    # Context-aware overall assessment
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

def save_utility_usage(user_id, water_gallons, electricity_kwh, gas_cubic_m, water_status, electricity_status, gas_status, efficiency_score=None, carbon_footprint=None):
    """Save utility usage data to the database for a specific user"""
    # Calculate points for this usage entry
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
    
    # Update user's total points (only for public users)
    user = session.query(User).filter(User.id == user_id).first()
    if user and user.is_public == 'public':
        current_points = user.total_points if user.total_points is not None else 0
        session.query(User).filter(User.id == user_id).update({
            User.total_points: current_points + points_earned
        })
    
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
    
    return usage

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
    """Calculate sustainability points based on utility usage levels - max 5 points per utility"""
    points = 0
    
    # Water usage scoring (lower is better) - max 5 points
    if water_gallons <= 50:
        points += 5   # Excellent
    elif water_gallons <= 100:
        points += 4   # Very Good
    elif water_gallons <= 150:
        points += 3   # Good
    elif water_gallons <= 200:
        points += 2   # Fair
    elif water_gallons <= 300:
        points += 1   # Poor
    else:
        points += 0   # Very Poor
    
    # Electricity usage scoring (lower is better) - max 5 points
    if electricity_kwh <= 200:
        points += 5   # Excellent
    elif electricity_kwh <= 400:
        points += 4   # Very Good
    elif electricity_kwh <= 600:
        points += 3   # Good
    elif electricity_kwh <= 800:
        points += 2   # Fair
    elif electricity_kwh <= 1000:
        points += 1   # Poor
    else:
        points += 0   # Very Poor
    
    # Gas usage scoring (lower is better) - max 5 points
    if gas_cubic_m <= 20:
        points += 5   # Excellent
    elif gas_cubic_m <= 40:
        points += 4   # Very Good
    elif gas_cubic_m <= 60:
        points += 3   # Good
    elif gas_cubic_m <= 80:
        points += 2   # Fair
    elif gas_cubic_m <= 100:
        points += 1   # Poor
    else:
        points += 0   # Very Poor
    
    return points

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
    """Get top ranking public users by points"""
    return session.query(User).filter(
        User.is_public == 'public'
    ).order_by(User.total_points.desc()).limit(limit).all()

def get_user_rank(user_id):
    """Get user's current rank among public users"""
    user = session.query(User).filter(User.id == user_id).first()
    if not user or user.is_public != 'public':
        return None
    
    user_points = user.total_points if user.total_points is not None else 0
    
    # Count users with higher points
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

# Initialize the database with materials
initialize_materials()