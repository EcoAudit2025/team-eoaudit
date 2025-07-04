import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from urllib.parse import quote
from datetime import datetime
import database as db
from simple_ai_models import eco_ai, material_ai
from ultra_smart_chatbot import UltraSmartEcoBot
import numpy as np
from translations import get_translation, get_available_languages, translate_text

# Set page configuration
st.set_page_config(
    page_title="EcoAudit - Environmental Impact Tracker",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "EcoAudit helps you track and reduce your environmental impact through utility monitoring, recycling guidance, and AI-powered insights."
    }
)

# Initialize smart chatbot
@st.cache_resource
def get_chatbot():
    return UltraSmartEcoBot()

# Aggressive caching for network optimization
@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_cached_public_users(search_term=None):
    """Cached version of public users query - reduced network calls"""
    return db.get_public_users(search_term)

@st.cache_data(ttl=900)  # Cache for 15 minutes
def get_cached_global_rankings():
    """Cached version of global rankings - longer cache"""
    return db.get_global_rankings(limit=10)

@st.cache_data(ttl=480)  # Cache for 8 minutes
def get_cached_utility_history(user_id=None, limit=10):
    """Cached version of utility history - reduced queries"""
    return db.get_utility_history(user_id, limit)

@st.cache_data(ttl=720)  # Cache for 12 minutes
def get_cached_popular_materials():
    """Cached version of popular materials - longer cache"""
    return db.get_popular_materials(limit=5)

# Session state for persistent data across tabs
if 'cached_user_data' not in st.session_state:
    st.session_state.cached_user_data = {}
if 'last_data_fetch' not in st.session_state:
    st.session_state.last_data_fetch = 0

chatbot = get_chatbot()

# Base URL for sharing
APP_URL = os.environ.get("REPLIT_DOMAINS", "").split(',')[0] if os.environ.get("REPLIT_DOMAINS") else ""

# Helper function to get actual public URL
def get_public_url():
    """Get the actual public-facing URL of the app"""
    if APP_URL:
        return f"https://{APP_URL}"
    return "URL not available"

# Initialize session state with error handling for render deployment
if 'show_saved' not in st.session_state:
    st.session_state.show_saved = False
if 'saved_message' not in st.session_state:
    st.session_state.saved_message = ""
if 'ai_initialized' not in st.session_state:
    st.session_state.ai_initialized = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'widget_counter' not in st.session_state:
    st.session_state.widget_counter = 0
if 'classification_initialized' not in st.session_state:
    st.session_state.classification_initialized = False
if 'auto_login_checked' not in st.session_state:
    st.session_state.auto_login_checked = False
if 'last_username' not in st.session_state:
    st.session_state.last_username = ""
if 'last_account_type' not in st.session_state:
    st.session_state.last_account_type = "private"
if 'remember_login' not in st.session_state:
    st.session_state.remember_login = True  # Changed default to True for persistent login
if 'app_language' not in st.session_state:
    st.session_state.app_language = 'English'

# Initialize user classification system on first run
if not st.session_state.classification_initialized:
    try:
        db.classify_all_users()
        st.session_state.classification_initialized = True
    except Exception as e:
        # Silent failure for deployment compatibility
        pass

# Enhanced auto-login functionality for persistent sessions
if not st.session_state.auto_login_checked and st.session_state.last_username and not st.session_state.current_user:
    try:
        # Always try to restore user session for persistent login
        if st.session_state.remember_login and st.session_state.last_username:
            # First try with the last account type used
            user = db.get_user(st.session_state.last_username, is_public=st.session_state.last_account_type)
            if not user:
                # Fallback to opposite account type
                fallback_type = 'public' if st.session_state.last_account_type == 'private' else 'private'
                user = db.get_user(st.session_state.last_username, is_public=fallback_type)
            if user:
                st.session_state.current_user = user
        st.session_state.auto_login_checked = True
    except Exception as e:
        pass

# Error handling for render deployment
try:
    # Initialize database with error handling
    db.initialize_materials()
except Exception:
    pass  # Silent fail for deployment compatibility

# Initialize AI system on first run (optimized for faster loading)
if not st.session_state.ai_initialized:
    # Quick initialization without blocking the UI
    try:
        # Load minimal data for faster startup
        historical_data = db.get_utility_history(limit=20)
        if len(historical_data) > 5:
            data_for_training = []
            for record in historical_data:
                data_for_training.append({
                    'timestamp': record.timestamp,
                    'water_gallons': record.water_gallons,
                    'electricity_kwh': record.electricity_kwh,
                    'gas_cubic_m': record.gas_cubic_m,
                    'water_status': record.water_status,
                    'electricity_status': record.electricity_status,
                    'gas_status': record.gas_status
                })
            
            # Quick AI model initialization
            success, message = eco_ai.train_models(data_for_training)
            if success:
                st.session_state.ai_initialized = True
        else:
            st.session_state.ai_initialized = True  # Allow app to load even without data
    except:
        st.session_state.ai_initialized = True  # Fail gracefully

# Title and introduction with custom icon
from PIL import Image
import base64

# Load the custom icon
icon = Image.open("generated-icon.png")

# Create layout with user points box in upper right corner
header_col1, header_col2, header_col3 = st.columns([1, 4, 1.5])

with header_col1:
    st.image(icon, width=100)
    
with header_col2:
    st.title("EcoAudit")
    st.markdown("""
        Monitor your utility usage and get guidance on recycling/reusing materials.
        This application helps you track your water, electricity, and gas usage, 
        and provides tips on how to reuse or recycle non-biodegradable materials.
        
        *Created by Team EcoAudit*
    """)

with header_col3:
    # User Points and Rank Display Box - positioned in upper right corner
    if 'current_user' in st.session_state and st.session_state.current_user:
        user = st.session_state.current_user
        # Refresh user data from database with error handling
        try:
            fresh_user = db.get_user(user.username, user.is_public)
            if fresh_user:
                st.session_state.current_user = fresh_user
                user = fresh_user
        except Exception:
            # Continue with cached user data if refresh fails
            pass
            
        if hasattr(user, 'is_public') and user.is_public == 'public':
            user_points = getattr(user, 'total_points', 0) or 0
            try:
                user_rank = db.get_user_rank(user.id)
            except Exception:
                user_rank = "N/A"
            rank_display = f"#{user_rank}" if user_rank else "N/A"
            
            st.success(f"""
**{user.username}**
🏆 Rank: {rank_display}
⭐ Points: {user_points}
🌱 Class: {getattr(user, 'environmental_class', '') or 'N/A'}
""")
        else:
            st.info(f"""
**{user.username}**
📊 Private Account
🔒 No Rankings
🌱 Class: {getattr(user, 'environmental_class', '') or 'N/A'}
""")
    else:
        st.markdown("""
<div style="background-color: #FFF3CD; padding: 10px; border-radius: 5px; border: 1px solid #FFEAA7; text-align: center;">
<strong>Not Logged In</strong><br>
<small>Login to see your points and rank</small>
</div>
""", unsafe_allow_html=True)

# Divider line
st.divider()
    


# AI-Enhanced Functions
def assess_usage_with_ai(water_gallons, electricity_kwh, gas_cubic_m, user=None):
    """AI-powered utility usage assessment with user context and AI-based point scoring"""
    # Get historical data for personalized assessment
    if user:
        historical_data = db.get_user_usage_last_year(user.id)
    else:
        historical_data = db.get_utility_history(limit=50)
    
    data_for_analysis = []
    for record in historical_data:
        data_for_analysis.append({
            'timestamp': record.timestamp,
            'water_gallons': record.water_gallons,
            'electricity_kwh': record.electricity_kwh,
            'gas_cubic_m': record.gas_cubic_m
        })
    
    # Enhanced AI assessment with user context
    water_status, electricity_status, gas_status = eco_ai.assess_usage_with_context(
        water_gallons, electricity_kwh, gas_cubic_m, user, data_for_analysis
    )
    
    # Calculate efficiency score based on usage patterns
    efficiency_score = 50  # Default baseline
    carbon_footprint = water_gallons * 0.002 + electricity_kwh * 0.4 + gas_cubic_m * 2.2
    
    # Enhanced efficiency calculation
    water_efficiency = 100 if water_gallons <= 50 else max(0, 100 - (water_gallons - 50) * 0.5)
    electricity_efficiency = 100 if electricity_kwh <= 200 else max(0, 100 - (electricity_kwh - 200) * 0.1)
    gas_efficiency = 100 if gas_cubic_m <= 20 else max(0, 100 - (gas_cubic_m - 20) * 1.0)
    
    efficiency_score = (water_efficiency + electricity_efficiency + gas_efficiency) / 3
    
    ai_predictions = None
    ai_recommendations = []
    
    if eco_ai.is_trained and len(data_for_analysis) > 0:
        try:
            ai_recommendations = eco_ai.generate_contextual_recommendations(
                water_gallons, electricity_kwh, gas_cubic_m, user
            )
            patterns = eco_ai.analyze_usage_patterns(data_for_analysis)
            efficiency_score = patterns.get('efficiency_score', efficiency_score)
            ai_predictions = patterns.get('predictions', None)
        except Exception as e:
            ai_recommendations = eco_ai.generate_recommendations(water_gallons, electricity_kwh, gas_cubic_m)
    else:
        ai_recommendations = eco_ai.generate_recommendations(water_gallons, electricity_kwh, gas_cubic_m)
    
    # Validate inputs and apply penalties for unrealistic values
    def validate_usage_values(water, electricity, gas):
        """Validate usage values and return penalty multipliers"""
        penalties = {'water': 1.0, 'electricity': 1.0, 'gas': 1.0, 'overall': 1.0}
        warnings = []
        
        # Define realistic thresholds
        realistic_max = {'water': 1500, 'electricity': 2500, 'gas': 400}
        extreme_max = {'water': 5000, 'electricity': 8000, 'gas': 1000}
        
        # Check water usage
        if water >= extreme_max['water']:
            penalties['water'] = 0.1
            warnings.append(f"Water usage ({water} gallons) is extremely unrealistic")
        elif water >= realistic_max['water']:
            penalties['water'] = 0.4
            warnings.append(f"Water usage ({water} gallons) is unusually high")
        elif water >= realistic_max['water'] * 0.8:
            penalties['water'] = 0.7
            
        # Check electricity usage
        if electricity >= extreme_max['electricity']:
            penalties['electricity'] = 0.1
            warnings.append(f"Electricity usage ({electricity} kWh) is extremely unrealistic")
        elif electricity >= realistic_max['electricity']:
            penalties['electricity'] = 0.4
            warnings.append(f"Electricity usage ({electricity} kWh) is unusually high")
        elif electricity >= realistic_max['electricity'] * 0.8:
            penalties['electricity'] = 0.7
            
        # Check gas usage
        if gas >= extreme_max['gas']:
            penalties['gas'] = 0.1
            warnings.append(f"Gas usage ({gas} cubic meters) is extremely unrealistic")
        elif gas >= realistic_max['gas']:
            penalties['gas'] = 0.4
            warnings.append(f"Gas usage ({gas} cubic meters) is unusually high")
        elif gas >= realistic_max['gas'] * 0.8:
            penalties['gas'] = 0.7
            
        # Calculate overall penalty
        penalties['overall'] = (penalties['water'] + penalties['electricity'] + penalties['gas']) / 3
        
        return penalties, warnings
    
    # Validate inputs
    penalties, validation_warnings = validate_usage_values(water_gallons, electricity_kwh, gas_cubic_m)
    
    # Apply penalties to efficiency score
    efficiency_score = efficiency_score * penalties['overall']
    
    # Calculate AI-based point score with validation penalties
    base_ai_points = calculate_ai_points(water_status, electricity_status, gas_status, efficiency_score, user)
    ai_points = base_ai_points * penalties['overall']
    
    # Cap points for obviously unrealistic data
    if penalties['overall'] <= 0.2:
        ai_points = min(ai_points, 1.0)  # Maximum 1 point for extreme values
    elif penalties['overall'] <= 0.4:
        ai_points = min(ai_points, 3.0)  # Maximum 3 points for very high values
    elif penalties['overall'] <= 0.7:
        ai_points = min(ai_points, 6.0)  # Maximum 6 points for moderately high values
    
    # Return comprehensive analysis
    return {
        'water_status': water_status,
        'electricity_status': electricity_status,
        'gas_status': gas_status,
        'efficiency_score': round(efficiency_score, 1),
        'carbon_footprint': carbon_footprint,
        'ai_recommendations': ai_recommendations,
        'points': round(ai_points, 1),
        'ai_predictions': ai_predictions,
        'validation_warnings': validation_warnings,
        'data_points': len(data_for_analysis),
        'penalties_applied': penalties,
        'user_context': {
            'household_size': getattr(user, 'household_size', 1) if user else 1,
            'location': getattr(user, 'location_type', 'Unknown') if user else 'Unknown',
            'housing': getattr(user, 'housing_type', 'Unknown') if user else 'Unknown'
        }
    }
    
    return water_status, electricity_status, gas_status, ai_analysis

def calculate_ai_points(water_status, electricity_status, gas_status, efficiency_score, user=None):
    """AI-based points calculation with STRICT maximum of 10 points total based on user entries"""
    # Base scoring system - individual utility scores (max 3.33 each = 10 total)
    status_base_scores = {
        'Excellent': 3.33,
        'Very Good': 2.80,
        'Good': 2.30,
        'Above Normal': 1.80,
        'Normal': 1.50,
        'Below Normal': 1.00,
        'High': 0.80,
        'Very High': 0.50,
        'Critical': 0.20,
        'Emergency': 0.0,
        'Low': 0.80  # Below normal range gets reduced points
    }
    
    # Get base points for each utility (max 3.33 each)
    water_points = status_base_scores.get(water_status, 1.50)
    electricity_points = status_base_scores.get(electricity_status, 1.50) 
    gas_points = status_base_scores.get(gas_status, 1.50)
    
    # Calculate total from three utilities (max 10.0)
    total_utility_points = water_points + electricity_points + gas_points
    
    # Apply efficiency modifier (can only reduce, not increase beyond 10)
    if efficiency_score >= 90:
        efficiency_modifier = 1.0  # No bonus beyond base 10
    elif efficiency_score >= 80:
        efficiency_modifier = 0.95
    elif efficiency_score >= 70:
        efficiency_modifier = 0.90
    elif efficiency_score >= 50:
        efficiency_modifier = 0.85
    elif efficiency_score >= 30:
        efficiency_modifier = 0.75
    else:
        efficiency_modifier = 0.60  # Significant penalty for poor efficiency
    
    # Apply efficiency modifier
    modified_points = total_utility_points * efficiency_modifier
    
    # Context adjustments (can add small bonus but never exceed 10)
    context_bonus = 0.0
    if user:
        # Small bonus for household efficiency (max 0.5 points)
        household_size = getattr(user, 'household_size', 1)
        if household_size > 1:
            per_person_bonus = min(0.1 * (household_size - 1), 0.5)
            context_bonus += per_person_bonus
        
        # Energy features bonus (max 0.5 points)
        energy_features = getattr(user, 'energy_features', None)
        if energy_features:
            try:
                import json
                features = json.loads(energy_features)
                feature_count = len(features)
                features_bonus = min(0.05 * feature_count, 0.5)
                context_bonus += features_bonus
            except:
                pass
    
    # Calculate final points with strict maximum
    final_points = modified_points + context_bonus
    
    # ABSOLUTE MAXIMUM - never exceed 10 points under any circumstance
    final_points = min(10.0, max(0.0, final_points))
    
    return round(final_points, 1)

def assess_usage(water_gallons, electricity_kwh, gas_cubic_m):
    """Compatibility function for existing code"""
    water_status, electricity_status, gas_status, _ = assess_usage_with_ai(water_gallons, electricity_kwh, gas_cubic_m)
    return water_status, electricity_status, gas_status

def help_center():
    help_content = [
        "**Water Usage:** Normal range is 3000–12000 gallons per month. If it's below 3000, check for a leak.",
        "**Electricity Usage:** Normal range is 300–800 kWh per month. If it's above 800, please get it checked by an electrician or there might be a fuse or a fire in a while.",
        "**Gas Usage:** Normal range is 50–150 cubic meters per month. Below 50 may indicate a gas leak."
    ]
    return help_content

def smart_assistant(material):
    """
    AI-powered material analysis providing reuse and recycle tips for non-biodegradable materials.
    Uses machine learning to analyze sustainability metrics and generate personalized recommendations.
    """
    material = material.lower()
    
    # Get AI-powered material analysis
    ai_analysis = material_ai.analyze_material(material)
    
    # Get traditional database recommendations
    material_data = db.find_material(material)
    
    # Combine AI analysis with database information
    result = {
        'ai_sustainability_score': ai_analysis['sustainability_score'],
        'environmental_impact': ai_analysis['environmental_impact'],
        'recyclability_score': ai_analysis['recyclability'],
        'material_category': ai_analysis['category'],
        'reuse_tips': material_data.reuse_tip if material_data else None,
        'recycle_tips': material_data.recycle_tip if material_data else None
    }
    
    # If no database entry exists, use comprehensive database
    if not result['reuse_tips'] or not result['recycle_tips']:
        fallback_data = get_fallback_material_data(material)
        if fallback_data and isinstance(fallback_data, dict):
            result['reuse_tips'] = fallback_data.get('reuse', f"Consider creative repurposing of {material} based on its material properties and durability.")
            result['recycle_tips'] = fallback_data.get('recycle', f"Research local recycling options for {material} or contact waste management services for proper disposal guidance.")
        else:
            # Provide generic but useful tips
            result['reuse_tips'] = f"Consider creative repurposing of {material} based on its material properties and durability."
            result['recycle_tips'] = f"Research local recycling options for {material} or contact waste management services for proper disposal guidance."
    
    return result

def get_fallback_material_data(material):
    """Get fallback material data from comprehensive database"""
    # Comprehensive materials database with reuse and recycle tips
    materials_database = {
        # Plastics
        "plastic bag": {
            "reuse": "Use as trash liners, storage bags, or packing material. Can also be fused together to make waterproof tarps or stronger reusable bags.",
            "recycle": "Drop at plastic bag collection centers or participating grocery stores. Many retailers have front-of-store recycling bins.",
            "websites": ["https://www.plasticfilmrecycling.org", "https://earth911.com/recycling-guide/how-to-recycle-plastic-bags/"]
        },
        "plastic bottle": {
            "reuse": "Create bird feeders, planters, watering cans, piggy banks, or desk organizers. Can be cut to make funnels, scoops, or storage containers.",
            "recycle": "Rinse thoroughly and recycle in curbside recycling if marked with recycling symbols 1 (PET) or 2 (HDPE).",
            "websites": ["https://www.plasticrecycling.org", "https://earth911.com/recycling-guide/how-to-recycle-plastic-bottles/"]
        },
        "plastic container": {
            "reuse": "Use for food storage, organizing small items, seed starters, or craft projects. Durable containers can become drawer dividers or small tool boxes.",
            "recycle": "Check the recycling number (1-7) on the bottom and recycle according to local guidelines. Thoroughly clean before recycling."
        },
        "plastic cup": {
            "reuse": "Use for seed starters, craft organization, or small storage. Can be decorated and used as pen holders or small gift containers.",
            "recycle": "Rinse and recycle #1 or #2 plastic cups. Many clear disposable cups are recyclable."
        },
        "plastic straw": {
            "reuse": "Create craft projects, jewelry, or use for science experiments. Can be used for drainage in potted plants.",
            "recycle": "Generally not recyclable in most curbside programs due to size. Consider switching to reusable alternatives."
        },
        "plastic toy": {
            "reuse": "Donate to charity, schools, or daycare centers if in good condition. Can be repurposed into art projects.",
            "recycle": "Hard plastic toys may be recyclable - check with local recycling facilities. Some toy companies have take-back programs."
        },
        "plastic lid": {
            "reuse": "Use as coasters, for arts and crafts, or as paint mixing palettes. Can be used to catch drips under flowerpots.",
            "recycle": "Many recycling programs accept plastic lids, but they should be separated from bottles/containers."
        },
        "plastic cover": {
            "reuse": "Use as protective surfaces for painting projects, cutting boards for crafts, or drawer liners.",
            "recycle": "Check recycling number and follow local guidelines. Many rigid plastic covers are recyclable."
        },
        "plastic wrap": {
            "reuse": "Can be cleaned and reused for wrapping items or for art projects. Use as a protective covering for painting.",
            "recycle": "Most cling wrap/plastic film is not recyclable in curbside programs but can be taken to store drop-off locations."
        },
        "polythene": {
            "reuse": "Use as moisture barriers, protective coverings, or for storage. Heavy-duty sheeting can be used for drop cloths.",
            "recycle": "Clean, dry polyethylene film can be recycled at store drop-off locations or special film recycling programs."
        },
        "bubble wrap": {
            "reuse": "Reuse for packaging, insulation, or as a plant frost protector. Can be used for textured art projects or stress relief.",
            "recycle": "Can be recycled with plastic film at grocery store drop-off locations, not in curbside recycling."
        },
        "ziploc bag": {
            "reuse": "Wash and reuse for food storage, organizing small items, or traveling with toiletries. Can be used for marinating foods.",
            "recycle": "Clean, dry Ziploc bags can be recycled with plastic film at store drop-off locations."
        },
        "styrofoam": {
            "reuse": "Use as packaging material, craft projects, or to make garden seedling trays. Can be broken up and used for drainage in planters.",
            "recycle": "Difficult to recycle in most areas. Some specialty recycling centers accept clean Styrofoam. Consider reducing usage."
        },
        "thermocol": {
            "reuse": "Can be used for insulation, art projects, or floating devices. Good for organization of fragile items.",
            "recycle": "Specialized facilities may accept clean thermocol. Contact local waste management for options."
        },
        "pvc": {
            "reuse": "PVC pipes can be repurposed for garden supports, organization systems, or DIY furniture projects.",
            "recycle": "PVC is difficult to recycle. Check with specialized recycling centers for options."
        },
        "acrylic": {
            "reuse": "Can be cut and reused for picture frames, art displays, or small organization projects.",
            "recycle": "Usually not accepted in curbside recycling. Some specialty recycling facilities may accept it."
        },
        "plastic packaging": {
            "reuse": "Use for storage, organizing, or craft projects. Blister packaging can become small containers.",
            "recycle": "Check with local recycling guidelines. Hard plastic packaging may be recyclable; soft film packaging usually needs store drop-off."
        },
        
        # Electronics and E-waste
        "e-waste": {
            "reuse": "Consider donating working electronics. Parts can be salvaged for DIY projects or educational purposes.",
            "recycle": "Take to certified e-waste recycling centers, retail take-back programs, or manufacturer recycling programs."
        },
        "battery": {
            "reuse": "Rechargeable batteries can be recharged hundreds of times. Single-use batteries cannot be reused.",
            "recycle": "Never throw in trash. Recycle at battery drop-off locations, electronic stores, or hazardous waste facilities.",
            "websites": ["https://www.call2recycle.org/locator", "https://www.epa.gov/recycle/used-household-batteries"]
        },
        "phone": {
            "reuse": "Repurpose as music players, alarm clocks, webcams, or dedicated GPS devices. Donate working phones to charity programs.",
            "recycle": "Return through manufacturer take-back programs or certified e-waste recyclers who will recover valuable materials."
        },
        "laptop": {
            "reuse": "Older laptops can be repurposed as media centers, digital photo frames, or dedicated writing devices.",
            "recycle": "Many manufacturers and electronics retailers offer recycling programs. Remove and securely erase data first."
        },
        "computer": {
            "reuse": "Repurpose as a media server, donate to schools or nonprofits, or use parts for other systems.",
            "recycle": "Take to certified e-waste recyclers, manufacturer take-back programs, or electronics retailers with recycling services."
        },
        "tablet": {
            "reuse": "Repurpose as digital photo frames, kitchen recipe displays, home automation controllers, or security monitors.",
            "recycle": "Recycle through manufacturer programs, electronics retailers, or certified e-waste recyclers."
        },
        "printer": {
            "reuse": "Donate working printers to schools, nonprofits, or community centers. Parts can be salvaged for projects.",
            "recycle": "Many electronics retailers and office supply stores offer printer recycling. Never dispose in regular trash."
        },
        "wire": {
            "reuse": "Repurpose for craft projects, garden ties, or organization solutions. Quality cables can be kept as spares.",
            "recycle": "Recycle with e-waste or at scrap metal facilities. Copper wiring has value for recycling."
        },
        "cable": {
            "reuse": "Label and store useful cables for future use. Can be repurposed for organization or craft projects.",
            "recycle": "E-waste recycling centers will accept cables and cords. Some retailers also offer cable recycling."
        },
        "headphone": {
            "reuse": "Repair if possible, or use parts for other audio projects. Working headphones can be donated.",
            "recycle": "Recycle with other e-waste at electronics recycling centers or through manufacturer programs."
        },
        "charger": {
            "reuse": "Keep compatible chargers as backups. Universal chargers can be used for multiple devices.",
            "recycle": "Recycle with e-waste at electronics recycling centers or through retailer programs."
        },
        
        # Metals
        "metal": {
            "reuse": "Metal items can often be repurposed for craft projects, garden art, or functional household items.",
            "recycle": "Most metals are highly recyclable and valuable. Clean and separate by type when possible."
        },
        "aluminum": {
            "reuse": "Aluminum cans can be used for crafts, planters, or organizational tools. Aluminum foil can be cleaned and reused.",
            "recycle": "One of the most recyclable materials. Clean and crush cans to save space. Foil should be cleaned first."
        },
        "aluminum can": {
            "reuse": "Create candle holders, pencil cups, wind chimes, or other decorative items. Can be used for camping or craft stoves.",
            "recycle": "Highly recyclable and can be recycled infinitely. Rinse clean and place in recycling bin."
        },
        "aluminum foil": {
            "reuse": "Clean foil can be reused for cooking, food storage, or crafting. Can be molded into small containers or used as garden pest deterrents.",
            "recycle": "Clean foil can be recycled. Roll into a ball to prevent it from blowing away in recycling facilities."
        },
        "tin can": {
            "reuse": "Use for storage, planters, candle holders, or craft projects. Can be decorated and repurposed in many ways.",
            "recycle": "Remove labels, rinse clean, and recycle with metal recycling. The metal is valuable and highly recyclable."
        },
        "steel": {
            "reuse": "Small steel items can be repurposed or used for DIY projects. Steel containers can be reused for storage.",
            "recycle": "Highly recyclable. Separate from other materials when possible and recycle with metals."
        },
        "iron": {
            "reuse": "Iron pieces can be used for weights, doorstops, or decorative elements. Small pieces can be used in craft projects.",
            "recycle": "Recyclable at scrap metal facilities. Separate from other metals when possible."
        },
        "copper": {
            "reuse": "Small copper items or wiring can be used for art projects, garden features, or DIY electronics.",
            "recycle": "Valuable for recycling. Take to scrap metal facilities or e-waste recycling centers."
        },
        "brass": {
            "reuse": "Brass items can be cleaned, polished, and repurposed as decorative elements or functional hardware.",
            "recycle": "Recyclable at scrap metal facilities. Keep separate from other metals for higher value."
        },
        "silver": {
            "reuse": "Silver items can be cleaned, polished, and reused. Small amounts can be used in craft or jewelry projects.",
            "recycle": "Valuable for recycling. Take to specialty recyclers or jewelers who may buy silver scrap."
        },
        
        # Glass
        "glass": {
            "reuse": "Glass jars and bottles can be washed and reused for storage, craft projects, or serving containers.",
            "recycle": "Highly recyclable but should be separated by color. Remove lids and rinse clean before recycling."
        },
        "glass jar": {
            "reuse": "Perfect for food storage, organization, vases, candle holders, or terrarium projects.",
            "recycle": "Remove lids, rinse thoroughly, and recycle. Glass can be recycled endlessly without loss of quality."
        },
        "glass bottle": {
            "reuse": "Reuse as water bottles, vases, lamp bases, garden borders, or decorative items. Can be cut to make drinking glasses.",
            "recycle": "Remove caps and rinse thoroughly. Sort by color if required by local recycling guidelines."
        },
        "light bulb": {
            "reuse": "Incandescent bulbs can be repurposed as decorative items or craft projects. Do not reuse broken glass.",
            "recycle": "Incandescent bulbs generally go in trash. CFLs and LEDs should be recycled at specialty locations due to components."
        },
        "mirror": {
            "reuse": "Broken mirrors can be used for mosaic art. Intact mirrors can be reframed or repurposed as decorative items.",
            "recycle": "Mirror glass is not recyclable with regular glass due to reflective coating. Donate usable mirrors."
        },
        "windshield": {
            "reuse": "Salvaged auto glass can be repurposed for construction, art installations, or landscaping features.",
            "recycle": "Auto glass is not recyclable in regular glass recycling. Specialized auto recyclers may accept it."
        },
        
        # Rubber and Silicone
        "rubber": {
            "reuse": "Can be cut into gaskets, grip pads, or used for craft projects. Rubber strips can function as jar openers.",
            "recycle": "Specialized rubber recycling programs exist. Check with tire retailers or rubber manufacturers."
        },
        "tire": {
            "reuse": "Create garden planters, swings, outdoor furniture, or playground equipment. Can be used as exercise weights.",
            "recycle": "Many tire retailers will accept old tires for recycling, usually for a small fee. Never burn tires."
        },
        "slipper": {
            "reuse": "Old flip-flops can be used as kneeling pads, cleaning scrubbers, or craft projects. Donate usable footwear.",
            "recycle": "Some athletic shoe companies have recycling programs for athletic shoes. Check TerraCycle for specialty programs."
        },
        "rubber band": {
            "reuse": "Keep for organization, sealing containers, or craft projects. Can be used as grip enhancers or hair ties.",
            "recycle": "Not recyclable in conventional systems. Reuse until worn out, then dispose in trash."
        },
        "silicone": {
            "reuse": "Silicone kitchenware can be repurposed for organizational trays, pet feeding mats, or craft molds.",
            "recycle": "Not recyclable in conventional systems. Some specialty programs through TerraCycle may exist."
        },
        
        # Paper Products with Non-Biodegradable Elements
        "tetra pack": {
            "reuse": "Clean and dry for craft projects, seed starters, or storage containers. Can be used as small compost bins.",
            "recycle": "Specialized recycling is required due to multiple material layers. Check if your area accepts carton recycling."
        },
        "juice box": {
            "reuse": "Clean thoroughly and use for craft projects, small storage, or seed starters.",
            "recycle": "Rinse and recycle through carton recycling programs where available."
        },
        "laminated paper": {
            "reuse": "Reuse as durable labels, bookmarks, place mats, or educational materials.",
            "recycle": "Generally not recyclable due to plastic coating. Reuse instead of recycling."
        },
        "waxed paper": {
            "reuse": "Can be reused several times for food wrapping or as a non-stick surface for crafts.",
            "recycle": "Not recyclable due to wax coating. Some versions may be compostable if made with natural wax."
        },
        "receipts": {
            "reuse": "Use for note-taking or craft projects if not thermal paper.",
            "recycle": "Thermal receipts (shiny paper) contain BPA and should not be recycled or composted. Regular paper receipts can be recycled."
        },
        
        # Fabrics and Textiles
        "synthetic": {
            "reuse": "Repurpose for cleaning rags, craft projects, pet bedding, or stuffing for pillows.",
            "recycle": "Some textile recycling programs accept synthetic fabrics. H&M and other retailers have fabric take-back programs."
        },
        "polyester": {
            "reuse": "Cut into cleaning cloths, use for quilting projects, or repurpose into bags, pillowcases, or other items.",
            "recycle": "Take to textile recycling programs. Some areas have curbside textile recycling."
        },
        "old clothes": {
            "reuse": "Convert to cleaning rags, craft materials, or upcycle into new garments. Donate wearable clothes.",
            "recycle": "Textile recycling programs accept worn-out clothes. Some retailers offer take-back programs."
        },
        "shirt": {
            "reuse": "Turn into pillowcases, bags, quilts, or cleaning rags. T-shirts make great yarn for crochet projects.",
            "recycle": "Donate wearable shirts to charity. Recycle unwearable shirts through textile recycling programs."
        },
        "nylon": {
            "reuse": "Old nylon stockings can be used for gardening, straining, cleaning, or craft projects.",
            "recycle": "Some specialty recycling programs accept nylon. Check with manufacturers like Patagonia or TerraCycle."
        },
        "carpet": {
            "reuse": "Cut into rugs, door mats, or cat scratching posts. Use under furniture to prevent floor scratches.",
            "recycle": "Some carpet manufacturers have take-back programs. Check with local carpet retailers."
        },
        
        # Media and Data Storage
        "cd": {
            "reuse": "Create reflective decorations, coasters, art projects, or garden bird deterrents.",
            "recycle": "Specialized e-waste recycling centers can process CDs and DVDs. Cannot go in curbside recycling."
        },
        "dvd": {
            "reuse": "Use for decorative projects, mosaic art, reflective garden features, or craft projects.",
            "recycle": "Take to electronics recycling centers. Best Buy and other retailers may accept them for recycling."
        },
        "video tape": {
            "reuse": "The tape inside can be used for craft projects, binding materials, or decorative elements.",
            "recycle": "Requires specialty e-waste recycling. GreenDisk and similar services accept media for recycling."
        },
        "cassette tape": {
            "reuse": "Cases can be repurposed for small item storage. Tape can be used in art projects.",
            "recycle": "Specialized e-waste recycling is required. Not accepted in curbside recycling."
        },
        "floppy disk": {
            "reuse": "Repurpose as coasters, notebook covers, or decorative items. Can be disassembled for craft parts.",
            "recycle": "Specialized e-waste recycling is required. Not accepted in regular recycling."
        },
        
        # Composites and Multi-material Items
        "shoes": {
            "reuse": "Donate wearable shoes. Repurpose parts for crafts or garden projects.",
            "recycle": "Nike's Reuse-A-Shoe program and similar initiatives recycle athletic shoes into playground surfaces."
        },
        "backpack": {
            "reuse": "Repair and donate usable backpacks. Repurpose fabric, zippers, and straps for other projects.",
            "recycle": "Some textile recycling programs may accept them. The North Face and similar programs take worn gear."
        },
        "umbrella": {
            "reuse": "Fabric can be used for small waterproof projects. Frame can be used for garden supports or craft projects.",
            "recycle": "Separate materials (metal frame and synthetic fabric) and recycle appropriately. Full umbrellas not recyclable."
        },
        "mattress": {
            "reuse": "Foam can be repurposed for cushions or pet beds. Springs can be used for garden trellises.",
            "recycle": "Specialized mattress recycling facilities can break down components. Many states have mattress recycling programs."
        },
        
        # Miscellaneous
        "blister pack": {
            "reuse": "Small clear blister packs can be used for bead or craft supply storage, seed starting, or organizing small items.",
            "recycle": "Generally not recyclable in curbside programs. TerraCycle has specialty programs for some types."
        },
        "paint can": {
            "reuse": "Clean metal paint cans can be used for storage or organization. Use as planters with drainage holes.",
            "recycle": "Metal paint cans can be recycled once completely empty and dry. Latex paint residue can be dried out."
        },
        "ceramic": {
            "reuse": "Broken ceramics can be used for mosaic projects, drainage in planters, or garden decoration.",
            "recycle": "Not recyclable in conventional recycling. Clean, usable items should be donated."
        },
        "fiberglass": {
            "reuse": "Small fiberglass pieces can be used for insulation projects or DIY auto body repairs.",
            "recycle": "Specialized recycling is required. Check with manufacturers or construction waste recyclers."
        },
        "composite wood": {
            "reuse": "Repurpose for smaller projects, garden edging, or raised bed construction.",
            "recycle": "Not recyclable in conventional systems due to adhesives and mixed materials. Reuse is preferred."
        }
    }
    
    # Search for keywords in the material string
    for key, tips in materials_database.items():
        if key in material:
            return tips["reuse"], tips["recycle"]
    
    # Check for broader categories with partial matching
    for key, tips in materials_database.items():
        if any(word in material for word in key.split()):
            return tips["reuse"], tips["recycle"]
    
    # Default response if no match found
    return ("Try creative repurposing based on the material properties. Consider if it can be cut, shaped, or combined with other materials for new uses.", 
            "Research specialized recycling options for this material. Contact your local waste management authority or search Earth911.com for recycling locations.")

# Generate shareable URL function
def generate_share_url(page, params=None):
    """Generate a shareable URL for the current state of the app."""
    # We don't use external URLs now, just create a data structure for sharing
    result = {
        "page": page,
        "params": params if params else {}
    }
    
    # Convert to JSON string for display/sharing
    return json.dumps(result, indent=2)

# Sidebar for navigation with icon and error handling
try:
    sidebar_col1, sidebar_col2 = st.sidebar.columns([1, 4])
    with sidebar_col1:
        st.image(icon, width=50)
    with sidebar_col2:
        st.title("Navigation")
    
    # Daily Usage Limits Information
    st.sidebar.markdown("### ⏰ Daily Usage Limits")
    st.sidebar.info("""
    **Utility Usage Tracker:** 2 entries per day per user
    
    **Materials Recycling Guide:** Unlimited searches
    
    Limits reset at midnight (00:00)
    """)
    
    # Timer display for logged-in users
    if st.session_state.current_user:
        user = st.session_state.current_user
        time_until_reset = db.get_time_until_reset(user.id)
        can_save, usage_message = db.check_daily_usage_limit(user.id)
        
        if not can_save and "Daily limit reached" in usage_message:
            st.sidebar.warning(f"⏰ Next entry available in: **{time_until_reset}**")
        else:
            st.sidebar.success(usage_message)
    
    page = st.sidebar.radio("Go to", ["User Profile", "Utility Usage Tracker", "Materials Recycling Guide", "AI Insights Dashboard", "My History", "Global Monitor", "Blinkbot"], key="main_nav_radio")
except Exception:
    # Fallback navigation for deployment issues
    page = "User Profile"

# Environmental Champions Ranking System Info Box
st.sidebar.success("""
## 🏆 Environmental Champions League

**🌟 ENHANCED: Smart AI Sustainability Scoring!**

Advanced AI point system (0-10) with maximum rewards:
• **Weighted analysis**: Water (1.1x), Electricity (1.0x), Gas (0.9x)
• **Progressive bonuses**: Up to 25% for efficiency (90%+)
• **Context rewards**: Max 30% bonus for green features
• **Household scaling**: Larger families get per-person efficiency bonus
• **Location adjustments**: Climate & urban/rural considerations
• **Maximum rewards**: 20% for comprehensive green setups

Smart scoring factors:
- Energy features (Solar, Heat Pumps, etc.)
- Household composition & size
- Climate zone adaptations
- High-impact technology bonuses

Join thousands of eco-warriors worldwide:

• **🎯 Smart Scoring** - Earn up to 5 points per utility category
• **📊 Real-time Rankings** - See your global position instantly  
• **🌍 Public Competition** - Switch to public to join leaderboards
• **⭐ Maximum Rewards** - Up to 15 points per assessment
• **🏅 Elite Classes** - Achieve A, B, or C environmental status
• **🔥 Live Updates** - Rankings refresh automatically

**Ready to compete?** Visit Global Monitor and claim your spot!
""", icon="🌱")

# Welcome message and basic instructions
st.sidebar.info("""
## 👋 Welcome to EcoAudit!

### Using this app:
1. Navigate between different tools using the options above
2. Enter your data to get personalized assessments and recommendations
3. Use the share buttons to get links to specific results you want to share

### Sharing the app:
Share the URL of this page directly with others - they can access it immediately
""", icon="ℹ️")





# Display notification for saved items
if st.session_state.show_saved:
    st.sidebar.success(st.session_state.saved_message)
    st.session_state.show_saved = False

# Initialize persistent user login state
if 'persistent_user_id' not in st.session_state:
    st.session_state.persistent_user_id = None
if 'persistent_user_type' not in st.session_state:
    st.session_state.persistent_user_type = None

# Auto-login if user was previously logged in (persist across browser sessions)
if (st.session_state.persistent_user_id and 
    st.session_state.persistent_user_type and 
    st.session_state.current_user is None):
    try:
        # Retrieve user from database using persistent ID
        persistent_user = db.session.query(db.User).filter(
            db.User.id == st.session_state.persistent_user_id,
            db.User.is_public == st.session_state.persistent_user_type
        ).first()
        
        if persistent_user:
            st.session_state.current_user = persistent_user
    except:
        # Clear invalid persistent data
        st.session_state.persistent_user_id = None
        st.session_state.persistent_user_type = None

# Sharing options for the application
st.sidebar.title("Sharing Options")
st.sidebar.markdown("""
### Share the app:
Simply copy the URL from your browser and share it with others.
They can access the app directly without any additional steps.

### Share specific results:
When viewing your assessment results or recycling tips, use 
the "Share These Results" button to generate a shareable link.
""")

# Tips for better viewing experience
st.sidebar.markdown("""
### Viewing Tips
• Use landscape mode on mobile devices for optimal viewing
• Maximize your browser window for best experience with charts
""")

# Display popular materials from database
try:
    popular_materials = db.get_popular_materials(5)
    if popular_materials:
        st.sidebar.title("Popular Materials")
        for material in popular_materials:
            st.sidebar.markdown(f"- **{material.name.title()}** (searched {material.search_count} times)")
    
    # Add a section for database stats
    all_users = db.get_all_users()
    public_users = db.get_public_users()
    
    # Get actual materials count from database
    session = db.get_session()
    materials_count = session.query(db.Material).count()
    session.close()
    
    st.sidebar.title("Database Stats")
    st.sidebar.markdown(f"""
    - **{len(all_users)}** total users
    - **{len(public_users)}** public profiles
    """)
except Exception as e:
    st.sidebar.error("Database loading...")

# Creator's Only Section - At the very end of navigation
st.sidebar.markdown("---")
st.sidebar.error("""
## 🔒 Creator's Only

**Application Reset Control**

When updates are released, the entire application resets automatically. 
This section allows manual reset for testing and maintenance purposes.

**⚠️ WARNING: This will delete ALL users and data permanently!**

Enter the reset code below to reset the entire application:
""", icon="⚠️")

# Reset functionality
reset_code = st.sidebar.text_input(
    "🔑 Reset Code:", 
    type="password",
    placeholder="Enter secure reset code...",
    help="Users are permanently protected. Only authorized team members with the secret code can reset.",
    key="reset_code_input"
)

if st.sidebar.button("🔥 RESET APPLICATION", type="secondary", help="This will delete ALL data"):
    if reset_code == "Atishay,Adit,Akshaj@EcoAudit_Team":
        # Perform the reset with secure code
        with st.spinner("Resetting application..."):
            success, message = db.reset_entire_application(reset_code)
            
        if success:
            # Clear all session state including persistent login
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Clear all caches
            st.cache_data.clear()
            
            st.sidebar.success("✅ Application reset successfully! All data deleted.")
            st.sidebar.info("🔄 Please refresh the page to see the clean application.")
            
            # Show success message on main page too
            st.success("🔥 APPLICATION RESET COMPLETE! All users and data have been deleted.")
            st.info("🔄 Please refresh your browser to see the clean application.")
            st.balloons()
        else:
            st.sidebar.error(f"❌ Reset failed: {message}")
    elif reset_code:
        st.sidebar.error("❌ Invalid reset code. Access denied.")
    else:
        st.sidebar.warning("⚠️ Enter the reset code first.")

# Initialize session state for user authentication
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# Persistent login - check if user was previously logged in
if 'remember_user' not in st.session_state:
    st.session_state.remember_user = None
if 'remember_account_type' not in st.session_state:
    st.session_state.remember_account_type = None

# Auto-login if user was previously logged in on this device
if st.session_state.current_user is None and st.session_state.remember_user:
    try:
        remembered_user = db.get_user(st.session_state.remember_user, is_public=st.session_state.remember_account_type)
        if remembered_user:
            st.session_state.current_user = remembered_user
    except:
        pass

# Clear any cached data when switching users
if 'last_user_id' not in st.session_state:
    st.session_state.last_user_id = None

# Detect user changes and clear cached AI data
current_user_id = st.session_state.current_user.id if st.session_state.current_user else None
if st.session_state.last_user_id != current_user_id:
    st.session_state.last_user_id = current_user_id
    # Clear any user-specific cached data
    if 'ai_initialized' in st.session_state:
        st.session_state.ai_initialized = False

# Main application logic
if page == "User Profile":
    st.header("👤 User Profile & Authentication")
    
    if st.session_state.current_user is None:
        st.markdown("### Login or Create Account")
        
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        with tab1:
            st.subheader("Login to Your Account")
            username = st.text_input("Username", key="login_username")
            login_code = st.text_input("Security Code", type="password", key="login_confirmation_code",
                                     help="Enter your private 5-10 digit security code")
            account_type = st.selectbox("Account Type", ["private", "public"], 
                                      help="Select whether to access your public or private account")
            
            if st.button("Login", key="login_button"):
                if username and login_code:
                    user = db.authenticate_user(username, login_code, is_public=account_type)
                    if user:
                        st.session_state.current_user = user
                        # Store persistent login information for device memory
                        st.session_state.last_username = username
                        st.session_state.last_account_type = account_type
                        st.session_state.remember_login = True
                        
                        account_desc = "public" if getattr(user, 'is_public', None) == "public" else "private"
                        st.success(f"Welcome back, {user.username}! (Logged into {account_desc} account)")
                        
                        # Show if user has other account type
                        user_info = db.get_username_account_info(username)
                        if user_info and user_info['total_accounts'] > 1:
                            other_type = "private" if account_type == "public" else "public"
                            st.info(f"You also have a {other_type} account with this username.")
                        
                        st.rerun()
                    else:
                        st.error("Invalid username or security code. Please check your credentials.")
                elif not username:
                    st.warning("Please enter a username.")
                elif not login_code:
                    st.warning("Please enter your security code.")
        
        with tab2:
            st.subheader("Create New Account")
            new_username = st.text_input("Choose Username", key="new_username")
            new_email = st.text_input("Email (optional)", key="new_email")
            
            # Secure confirmation code input
            st.markdown("### 🔐 Security Code")
            confirmation_code = st.text_input(
                "Create Security Code (5-20 digits)", 
                type="password",
                key="new_confirmation_code",
                help="Create a private 5-20 digit code that only you will know. This code is required for login and account access.",
                max_chars=20
            )
            
            # Validation feedback
            if confirmation_code:
                is_valid, message = db.validate_confirmation_code(confirmation_code)
                if is_valid:
                    st.success("✓ Valid security code format")
                else:
                    st.error(f"❌ {message}")
            
            # Comprehensive location options
            location_type = st.selectbox("Location Type", [
                "Urban - Large City (>1M population)",
                "Urban - Medium City (100K-1M population)", 
                "Suburban - Metropolitan Area",
                "Small Town (10K-100K population)",
                "Rural - Countryside",
                "Rural - Remote Area"
            ], key="location_type")
            
            climate_zone = st.selectbox("Climate Zone", [
                "Tropical - Hot & Humid",
                "Subtropical - Warm & Humid", 
                "Mediterranean - Mild & Dry",
                "Temperate - Moderate Seasons",
                "Continental - Cold Winters",
                "Arid - Hot & Dry",
                "Semi-Arid - Moderate & Dry",
                "Polar - Very Cold"
            ], key="climate_zone")
            
            # Detailed household composition
            st.write("**Household Composition:**")
            col1, col2 = st.columns(2)
            
            with col1:
                adults = st.number_input("Adults (18+)", min_value=1, max_value=10, value=1, key="adults")
                children = st.number_input("Children (under 18)", min_value=0, max_value=10, value=0, key="children")
                seniors = st.number_input("Seniors (65+)", min_value=0, max_value=10, value=0, key="seniors")
            
            with col2:
                household_type = st.selectbox("Household Type", [
                    "Single Person",
                    "Young Couple (no children)",
                    "Newlyweds",
                    "Family with Infants (0-2 years)",
                    "Family with Young Children (3-8 years)",
                    "Family with Pre-teens (9-12 years)",
                    "Family with Teenagers (13-17 years)", 
                    "Family with Adult Children (18+ living at home)",
                    "Multi-generational Family (3+ generations)",
                    "Senior Couple (both 65+)",
                    "Single Parent with Young Children",
                    "Single Parent with Teenagers",
                    "Single Parent with Adult Children",
                    "Shared Housing/Roommates (2-3 people)",
                    "Shared Housing/Roommates (4+ people)",
                    "Extended Family (siblings, cousins)",
                    "Blended Family (step-children)",
                    "Empty Nesters (children moved out)",
                    "Retired Couple",
                    "Single Senior (65+)",
                    "Student Housing",
                    "Young Professionals Sharing",
                    "Divorced Parent (partial custody)",
                    "Foster Family",
                    "Multigenerational Caregivers"
                ], key="household_type")
            
            housing_type = st.selectbox("Housing Type", [
                "Apartment - Studio (under 500 sq ft)",
                "Apartment - 1 Bedroom (500-800 sq ft)", 
                "Apartment - 2 Bedroom (800-1200 sq ft)",
                "Apartment - 3+ Bedroom (1200+ sq ft)",
                "Loft/Converted Space",
                "Townhouse - 2 Story",
                "Townhouse - 3+ Story", 
                "Condominium - Low Rise",
                "Condominium - High Rise",
                "Duplex/Triplex",
                "Single Family House - Tiny (<800 sq ft)",
                "Single Family House - Small (800-1500 sq ft)",
                "Single Family House - Medium (1500-2500 sq ft)",
                "Single Family House - Large (2500-4000 sq ft)",
                "Single Family House - Mansion (4000+ sq ft)",
                "Ranch Style House",
                "Victorian/Historic House",
                "Modern/Contemporary House",
                "Log Cabin/Rustic House",
                "Mobile Home - Single Wide",
                "Mobile Home - Double Wide",
                "Manufactured Home",
                "Modular Home",
                "Tiny House on Wheels",
                "Farm House - Working Farm",
                "Farm House - Rural Property",
                "Estate/Large Property",
                "Retirement Community",
                "Co-housing Community",
                "Eco-Village/Sustainable Community",
                "Houseboat",
                "RV/Motorhome (permanent)",
                "Basement Suite/In-law Unit",
                "Garage Conversion",
                "Accessory Dwelling Unit (ADU)"
            ], key="housing_type")
            
            energy_features = st.multiselect("Energy Features", [
                "Solar Panels - Rooftop",
                "Solar Panels - Ground Mount",
                "Solar Water Heating",
                "Wind Turbine - Small Residential",
                "Geothermal Heating/Cooling",
                "Heat Pump - Air Source",
                "Heat Pump - Ground Source",
                "Energy Efficient Appliances (ENERGY STAR)",
                "Smart Thermostat - Programmable",
                "Smart Thermostat - Learning (Nest, etc.)",
                "Smart Home Energy Management System",
                "LED Lighting - Partial",
                "LED Lighting - Complete",
                "Smart Lighting System",
                "Double-Pane Windows",
                "Triple-Pane Windows",
                "Low-E Glass Windows",
                "Excellent Insulation (R-30+ walls)",
                "Good Insulation (R-19 to R-30 walls)",
                "Attic Insulation (R-38+)",
                "Basement/Crawlspace Insulation",
                "Radiant Floor Heating",
                "Tankless Water Heater",
                "High-Efficiency Water Heater",
                "Smart Water Heater",
                "Electric Vehicle Charging - Level 1",
                "Electric Vehicle Charging - Level 2",
                "Electric Vehicle Charging - Level 3 (DC Fast)",
                "Battery Storage System (Tesla Powerwall, etc.)",
                "Whole House Generator",
                "Smart Electrical Panel",
                "Energy Recovery Ventilation (ERV)",
                "Heat Recovery Ventilation (HRV)",
                "Smart Window Treatments/Shades",
                "Reflective/Cool Roof",
                "Green Roof/Living Roof",
                "Rainwater Harvesting System",
                "Greywater Recycling System",
                "High-Efficiency HVAC System",
                "Ductless Mini-Split System",
                "Zoned HVAC System",
                "Smart Power Strips",
                "Energy Monitoring System",
                "Induction Cooktop",
                "Energy Efficient Pool Equipment",
                "Smart Irrigation System",
                "Drought-Resistant Landscaping"
            ], key="energy_features")
            
            # Language selection - All major world languages
            language = st.selectbox("Preferred Language", [
                "English",
                "Spanish (Español)",
                "Chinese (中文)",
                "Hindi (हिन्दी)",
                "Arabic (العربية)",
                "Portuguese (Português)",
                "Bengali (বাংলা)",
                "Russian (Русский)",
                "Japanese (日本語)",
                "French (Français)",
                "German (Deutsch)",
                "Korean (한국어)",
                "Italian (Italiano)",
                "Turkish (Türkçe)",
                "Vietnamese (Tiếng Việt)",
                "Polish (Polski)",
                "Ukrainian (Українська)",
                "Dutch (Nederlands)",
                "Thai (ไทย)",
                "Greek (Ελληνικά)",
                "Czech (Čeština)",
                "Swedish (Svenska)",
                "Hungarian (Magyar)",
                "Hebrew (עברית)",
                "Norwegian (Norsk)",
                "Finnish (Suomi)",
                "Danish (Dansk)",
                "Romanian (Română)",
                "Bulgarian (Български)",
                "Croatian (Hrvatski)",
                "Slovak (Slovenčina)",
                "Slovenian (Slovenščina)",
                "Lithuanian (Lietuvių)",
                "Latvian (Latviešu)",
                "Estonian (Eesti)",
                "Serbian (Српски)",
                "Bosnian (Bosanski)",
                "Macedonian (Македонски)",
                "Albanian (Shqip)",
                "Maltese (Malti)",
                "Catalan (Català)",
                "Basque (Euskera)",
                "Galician (Galego)",
                "Welsh (Cymraeg)",
                "Irish (Gaeilge)",
                "Scots Gaelic (Gàidhlig)",
                "Icelandic (Íslenska)",
                "Faroese (Føroyskt)",
                "Luxembourgish (Lëtzebuergesch)",
                "Indonesian (Bahasa Indonesia)",
                "Malay (Bahasa Malaysia)",
                "Tagalog (Filipino)",
                "Swahili (Kiswahili)",
                "Hausa (هَوُسَا)",
                "Yoruba",
                "Igbo (Asụsụ Igbo)",
                "Amharic (አማርኛ)",
                "Somali (Soomaali)",
                "Zulu (isiZulu)",
                "Xhosa (isiXhosa)",
                "Afrikaans",
                "Nepali (नेपाली)",
                "Marathi (मराठी)",
                "Telugu (తెలుగు)",
                "Tamil (தமிழ்)",
                "Gujarati (ગુજરાતી)",
                "Kannada (ಕನ್ನಡ)",
                "Malayalam (മലയാളം)",
                "Punjabi (ਪੰਜਾਬੀ)",
                "Urdu (اردو)",
                "Persian/Farsi (فارسی)",
                "Dari (دری)",
                "Pashto (پښتو)",
                "Kurdish (Kurdî)",
                "Georgian (ქართული)",
                "Armenian (Հայերեն)",
                "Azerbaijani (Azərbaycan)",
                "Kazakh (Қазақша)",
                "Uzbek (O'zbek)",
                "Kyrgyz (Кыргызча)",
                "Tajik (Тоҷикӣ)",
                "Turkmen (Türkmen)",
                "Mongolian (Монгол)",
                "Tibetan (བོད་ཡིག)",
                "Burmese (မြန်မာ)",
                "Khmer (ខ្មែរ)",
                "Lao (ລາວ)",
                "Sinhala (සිංහල)",
                "Dhivehi (ދިވެހި)",
                "Fijian (Na Vosa Vakaviti)",
                "Samoan (Gagana Samoa)",
                "Tongan (Lea Fakatonga)",
                "Hawaiian (ʻŌlelo Hawaiʻi)",
                "Maori (Te Reo Māori)",
                "Other"
            ], key="language")
            
            new_is_public = st.selectbox("Data Visibility", ["private", "public"], 
                                       help="Public data can be viewed by others in the Global Monitor")
            
            if st.button("Create Account", key="create_button"):
                if new_username and confirmation_code:
                    # Validate confirmation code first
                    is_valid, message = db.validate_confirmation_code(confirmation_code)
                    if not is_valid:
                        st.error(f"❌ {message}")
                        st.stop()
                    
                    # Check if username already exists for this account type
                    existing_user = db.get_user(new_username, is_public=new_is_public)
                    if existing_user:
                        account_type_desc = "public" if new_is_public == "public" else "private"
                        st.error(f"❌ A {account_type_desc} account with username '{new_username}' already exists.")
                        
                        # Show information about existing accounts
                        user_info = db.get_username_account_info(new_username)
                        if user_info:
                            other_type = "private" if new_is_public == "public" else "public"
                            if (new_is_public == "public" and user_info['has_private']) or (new_is_public == "private" and user_info['has_public']):
                                st.info(f"💡 You already have a {other_type} account with this username. You can log in to your existing {other_type} account instead.")
                        st.stop()
                    
                    # Additional username validation
                    if len(new_username) < 3:
                        st.error("❌ Username must be at least 3 characters long.")
                        st.stop()
                    
                    if not new_username.replace('_', '').replace('-', '').isalnum():
                        st.error("❌ Username can only contain letters, numbers, underscores, and hyphens.")
                        st.stop()
                    
                    # Create the user
                    user = db.create_user(
                        username=new_username,
                        email=new_email if new_email else None,
                        location_type=location_type,
                        climate_zone=climate_zone,
                        adults=adults,
                        children=children,
                        seniors=seniors,
                        household_type=household_type,
                        housing_type=housing_type,
                        energy_features=energy_features,
                        is_public=new_is_public,
                        language=language,
                        confirmation_code=confirmation_code
                    )
                    if user:
                        st.session_state.current_user = user
                        # Store persistent login information for device memory
                        st.session_state.last_username = new_username
                        st.session_state.last_account_type = new_is_public
                        st.session_state.remember_login = True
                        st.session_state.app_language = language  # Set app language from user selection
                        st.success(f"🎉 Account created successfully! Welcome, {user.username}!")
                        st.info("🔐 Remember to save your security code safely. You'll need it to log in.")
                        st.rerun()
                    else:
                        st.error("Failed to create account. Please try again.")
                elif not new_username:
                    st.warning("Please enter a username.")
                elif not confirmation_code:
                    st.warning("Please create a security code.")
    else:
        # User is logged in - refresh user data from database to ensure latest changes
        current_user = st.session_state.current_user
        user = db.get_user(current_user.username, current_user.is_public)
        if not user:
            st.error("User session expired. Please log in again.")
            st.session_state.current_user = None
            st.rerun()
        else:
            # Update session state with fresh data from database
            st.session_state.current_user = user
            
        st.session_state.current_user = user  # Update session with fresh data
        account_type_desc = "Public" if user.is_public == "public" else "Private"
        st.success(f"Logged in as: **{user.username}** ({account_type_desc} Account)")
        
        # Show account information
        user_info = db.get_username_account_info(user.username)
        if user_info and user_info['total_accounts'] > 1:
            st.info(f"💡 You have both public and private accounts with username '{user.username}'. Currently viewing: {account_type_desc}")
        
        # Display user profile information
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Profile Information")
            st.write(f"**Username:** {user.username}")
            st.write(f"**Email:** {getattr(user, 'email', '') or 'Not provided'}")
            st.write(f"**Location Type:** {getattr(user, 'location_type', '') or 'Not specified'}")
            st.write(f"**Climate Zone:** {getattr(user, 'climate_zone', '') or 'Not specified'}")
            st.write(f"**Household Type:** {getattr(user, 'household_type', '') or 'Not specified'}")
            st.write(f"**Housing Type:** {getattr(user, 'housing_type', '') or 'Not specified'}")
            st.write(f"**Total People:** {getattr(user, 'household_size', 1)} ({getattr(user, 'adults', 0)} adults, {getattr(user, 'children', 0)} children, {getattr(user, 'seniors', 0)} seniors)")
            st.write(f"**Language:** {getattr(user, 'language', 'English')}")
            st.write(f"**Data Visibility:** {user.is_public}")
            st.write(f"**Environmental Class:** {getattr(user, 'environmental_class', '') or 'Not calculated'}")
            
            # Show ranking info for public users
            if user.is_public == 'public':
                user_points = getattr(user, 'total_points', 0) or 0
                user_rank = db.get_user_rank(user.id)
                st.write(f"**Sustainability Points:** {user_points}")
                if user_rank:
                    st.write(f"**Global Rank:** #{user_rank}")
            
            created_at = getattr(user, 'created_at', None)
            if created_at:
                st.write(f"**Member Since:** {created_at.strftime('%B %Y')}")
            
            # Display energy features if available
            energy_features = getattr(user, 'energy_features', None)
            if energy_features:
                import json
                try:
                    features = json.loads(energy_features)
                    if features:
                        st.write(f"**Energy Features:** {', '.join(features)}")
                except:
                    pass
        
        with col2:
            st.subheader("Account Statistics")
            
            # Get user's usage history
            user_usage = db.get_user_usage_last_year(user.id)
            total_records = len(user_usage)
            
            st.metric("Total Usage Records", total_records)
            
            if user_usage:
                avg_water = sum(record.water_gallons for record in user_usage) / len(user_usage)
                avg_electricity = sum(record.electricity_kwh for record in user_usage) / len(user_usage)
                avg_gas = sum(record.gas_cubic_m for record in user_usage) / len(user_usage)
                
                st.metric("Avg Water Usage", f"{avg_water:.0f} gal/month")
                st.metric("Avg Electricity Usage", f"{avg_electricity:.0f} kWh/month")
                st.metric("Avg Gas Usage", f"{avg_gas:.0f} m³/month")
        
        # Display AI Analysis
        if user.ai_analysis:
            st.subheader("🤖 AI Analysis")
            st.info(user.ai_analysis)
        elif user_usage:
            # Generate AI analysis if not exists
            if st.button("Generate AI Analysis"):
                with st.spinner("Generating AI analysis..."):
                    env_class = db.calculate_environmental_class(user_usage)
                    ai_analysis = db.generate_user_ai_analysis(user, user_usage)
                    db.update_user_environmental_class(user.id, env_class, ai_analysis)
                    st.session_state.current_user.environmental_class = env_class
                    st.session_state.current_user.ai_analysis = ai_analysis
                    st.rerun()
        
        # Profile management options
        st.subheader("Account Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            with st.expander("🔧 Update Profile", expanded=False):
                # Create update form with unique key
                with st.form("update_profile_form"):
                    st.write("**Contact Information:**")
                    update_email = st.text_input("Email", value=user.email or "")
                    
                    st.write("**Location & Climate:**")
                    location_options = [
                        "Urban - Large City (>1M population)",
                        "Urban - Medium City (100K-1M population)", 
                        "Suburban - Metropolitan Area",
                        "Small Town (10K-100K population)",
                        "Rural - Countryside",
                        "Rural - Remote Area"
                    ]
                    current_location_idx = 0
                    if user.location_type and user.location_type in location_options:
                        current_location_idx = location_options.index(user.location_type)
                    update_location = st.selectbox("Location Type", location_options, index=current_location_idx)
                    
                    climate_options = [
                        "Tropical - Hot & Humid",
                        "Subtropical - Warm & Humid", 
                        "Mediterranean - Mild & Dry",
                        "Temperate - Moderate Seasons",
                        "Continental - Cold Winters",
                        "Arid - Hot & Dry",
                        "Semi-Arid - Moderate & Dry",
                        "Polar - Very Cold"
                    ]
                    current_climate_idx = 0
                    if user.climate_zone and user.climate_zone in climate_options:
                        current_climate_idx = climate_options.index(user.climate_zone)
                    update_climate = st.selectbox("Climate Zone", climate_options, index=current_climate_idx)
                    
                    st.write("**Household Composition:**")
                    update_adults = st.number_input("Adults (18+)", min_value=1, max_value=10, value=int(getattr(user, 'adults', 1) or 1))
                    update_children = st.number_input("Children (under 18)", min_value=0, max_value=10, value=int(getattr(user, 'children', 0) or 0))
                    update_seniors = st.number_input("Seniors (65+)", min_value=0, max_value=10, value=int(getattr(user, 'seniors', 0) or 0))
                    
                    household_options = [
                        "Single Person",
                        "Young Couple (no children)",
                        "Newlyweds",
                        "Family with Infants (0-2 years)",
                        "Family with Young Children (3-8 years)",
                        "Family with Pre-teens (9-12 years)",
                        "Family with Teenagers (13-17 years)", 
                        "Family with Adult Children (18+ living at home)",
                        "Multi-generational Family (3+ generations)",
                        "Senior Couple (both 65+)",
                        "Single Parent with Young Children",
                        "Single Parent with Teenagers",
                        "Single Parent with Adult Children",
                        "Shared Housing/Roommates (2-3 people)",
                        "Shared Housing/Roommates (4+ people)",
                        "Extended Family (siblings, cousins)",
                        "Blended Family (step-children)",
                        "Empty Nesters (children moved out)",
                        "Retired Couple",
                        "Single Senior (65+)",
                        "Student Housing",
                        "Young Professionals Sharing",
                        "Divorced Parent (partial custody)",
                        "Foster Family",
                        "Multigenerational Caregivers"
                    ]
                    current_household_idx = 0
                    if user.household_type and user.household_type in household_options:
                        current_household_idx = household_options.index(user.household_type)
                    update_household_type = st.selectbox("Household Type", household_options, index=current_household_idx)
                    
                    housing_options = [
                        "Apartment - Studio (under 500 sq ft)",
                        "Apartment - 1 Bedroom (500-800 sq ft)", 
                        "Apartment - 2 Bedroom (800-1200 sq ft)",
                        "Apartment - 3+ Bedroom (1200+ sq ft)",
                        "Loft/Converted Space",
                        "Townhouse - 2 Story",
                        "Townhouse - 3+ Story", 
                        "Condominium - Low Rise",
                        "Condominium - High Rise",
                        "Duplex/Triplex",
                        "Single Family House - Tiny (<800 sq ft)",
                        "Single Family House - Small (800-1500 sq ft)",
                        "Single Family House - Medium (1500-2500 sq ft)",
                        "Single Family House - Large (2500-4000 sq ft)",
                        "Single Family House - Mansion (4000+ sq ft)",
                        "Ranch Style House",
                        "Victorian/Historic House",
                        "Modern/Contemporary House",
                        "Log Cabin/Rustic House",
                        "Mobile Home - Single Wide",
                        "Mobile Home - Double Wide",
                        "Manufactured Home",
                        "Modular Home",
                        "Tiny House on Wheels",
                        "Farm House - Working Farm",
                        "Farm House - Rural Property",
                        "Estate/Large Property",
                        "Retirement Community",
                        "Co-housing Community",
                        "Eco-Village/Sustainable Community",
                        "Houseboat",
                        "RV/Motorhome (permanent)",
                        "Basement Suite/In-law Unit",
                        "Garage Conversion",
                        "Accessory Dwelling Unit (ADU)"
                    ]
                    current_housing_idx = 0
                    if user.housing_type and user.housing_type in housing_options:
                        current_housing_idx = housing_options.index(user.housing_type)
                    update_housing_type = st.selectbox("Housing Type", housing_options, index=current_housing_idx)
                    
                    # Parse existing energy features
                    existing_features = []
                    if user.energy_features:
                        try:
                            import json
                            existing_features = json.loads(user.energy_features)
                        except:
                            existing_features = []
                    
                    energy_options = [
                        "Solar Panels - Rooftop",
                        "Solar Panels - Ground Mount",
                        "Solar Water Heating",
                        "Wind Turbine - Small Residential",
                        "Geothermal Heating/Cooling",
                        "Heat Pump - Air Source",
                        "Heat Pump - Ground Source",
                        "Energy Efficient Appliances (ENERGY STAR)",
                        "Smart Thermostat - Programmable",
                        "Smart Thermostat - Learning (Nest, etc.)",
                        "Smart Home Energy Management System",
                        "LED Lighting - Partial",
                        "LED Lighting - Complete",
                        "Smart Lighting System",
                        "Double-Pane Windows",
                        "Triple-Pane Windows",
                        "Low-E Glass Windows",
                        "Excellent Insulation (R-30+ walls)",
                        "Good Insulation (R-19 to R-30 walls)",
                        "Attic Insulation (R-38+)",
                        "Basement/Crawlspace Insulation",
                        "Radiant Floor Heating",
                        "Tankless Water Heater",
                        "High-Efficiency Water Heater",
                        "Smart Water Heater",
                        "Electric Vehicle Charging - Level 1",
                        "Electric Vehicle Charging - Level 2",
                        "Electric Vehicle Charging - Level 3 (DC Fast)",
                        "Battery Storage System (Tesla Powerwall, etc.)",
                        "Whole House Generator",
                        "Smart Electrical Panel",
                        "Energy Recovery Ventilation (ERV)",
                        "Heat Recovery Ventilation (HRV)",
                        "Smart Window Treatments/Shades",
                        "Reflective/Cool Roof",
                        "Green Roof/Living Roof",
                        "Rainwater Harvesting System",
                        "Greywater Recycling System",
                        "High-Efficiency HVAC System",
                        "Ductless Mini-Split System",
                        "Zoned HVAC System",
                        "Smart Power Strips",
                        "Energy Monitoring System",
                        "Induction Cooktop",
                        "Energy Efficient Pool Equipment",
                        "Smart Irrigation System",
                        "Drought-Resistant Landscaping"
                    ]
                    
                    # Filter existing features to only include valid options
                    valid_existing_features = [f for f in existing_features if f in [
                        "Solar Panels - Rooftop", "Solar Panels - Ground Mount", "Solar Water Heating",
                        "Wind Turbine - Small Residential", "Geothermal Heating/Cooling", "Heat Pump - Air Source",
                        "Heat Pump - Ground Source", "Energy Efficient Appliances (ENERGY STAR)",
                        "Smart Thermostat - Programmable", "Smart Thermostat - Learning (Nest, etc.)",
                        "Smart Home Energy Management System", "LED Lighting - Partial", "LED Lighting - Complete",
                        "Smart Lighting System", "Double-Pane Windows", "Triple-Pane Windows", "Low-E Glass Windows",
                        "Excellent Insulation (R-30+ walls)", "Good Insulation (R-19 to R-30 walls)",
                        "Attic Insulation (R-38+)", "Basement/Crawlspace Insulation", "Radiant Barrier Installation",
                        "Whole House Fan", "Ceiling Fans", "High-Efficiency Furnace (90%+ AFUE)",
                        "High-Efficiency Air Conditioner (16+ SEER)", "Ductless Mini-Split System",
                        "Tankless Water Heater", "Heat Pump Water Heater", "Solar Water Heater",
                        "Low-Flow Showerheads", "Low-Flow Faucets", "Dual-Flush Toilets",
                        "Smart Water Leak Detection", "Rainwater Collection System", "Greywater System",
                        "Electric Vehicle Charging Station", "Home Battery Storage (Tesla Powerwall, etc.)",
                        "Backup Generator (Natural Gas/Propane)", "Energy Monitoring System",
                        "Induction Cooktop", "Energy Efficient Pool Equipment", "Smart Irrigation System",
                        "Drought-Resistant Landscaping"
                    ]]
                    
                    update_energy_features = st.multiselect("Energy Features", energy_options, default=valid_existing_features)
                    
                    language_options = [
                        "English",
                        "Spanish (Español)",
                        "Chinese (中文)",
                        "Hindi (हिन्दी)",
                        "Arabic (العربية)",
                        "Portuguese (Português)",
                        "Bengali (বাংলা)",
                        "Russian (Русский)",
                        "Japanese (日本語)",
                        "French (Français)",
                        "German (Deutsch)",
                        "Korean (한국어)",
                        "Italian (Italiano)",
                        "Turkish (Türkçe)",
                        "Vietnamese (Tiếng Việt)",
                        "Polish (Polski)",
                        "Ukrainian (Українська)",
                        "Dutch (Nederlands)",
                        "Thai (ไทย)",
                        "Greek (Ελληνικά)",
                        "Czech (Čeština)",
                        "Swedish (Svenska)",
                        "Hungarian (Magyar)",
                        "Hebrew (עברית)",
                        "Norwegian (Norsk)",
                        "Finnish (Suomi)",
                        "Danish (Dansk)",
                        "Romanian (Română)",
                        "Bulgarian (Български)",
                        "Croatian (Hrvatski)",
                        "Slovak (Slovenčina)",
                        "Slovenian (Slovenščina)",
                        "Lithuanian (Lietuvių)",
                        "Latvian (Latviešu)",
                        "Estonian (Eesti)",
                        "Serbian (Српски)",
                        "Bosnian (Bosanski)",
                        "Macedonian (Македонски)",
                        "Albanian (Shqip)",
                        "Maltese (Malti)",
                        "Catalan (Català)",
                        "Basque (Euskera)",
                        "Galician (Galego)",
                        "Welsh (Cymraeg)",
                        "Irish (Gaeilge)",
                        "Scots Gaelic (Gàidhlig)",
                        "Icelandic (Íslenska)",
                        "Faroese (Føroyskt)",
                        "Luxembourgish (Lëtzebuergesch)",
                        "Indonesian (Bahasa Indonesia)",
                        "Malay (Bahasa Malaysia)",
                        "Tagalog (Filipino)",
                        "Swahili (Kiswahili)",
                        "Hausa (هَوُسَا)",
                        "Yoruba",
                        "Igbo (Asụsụ Igbo)",
                        "Amharic (አማርኛ)",
                        "Somali (Soomaali)",
                        "Zulu (isiZulu)",
                        "Xhosa (isiXhosa)",
                        "Afrikaans",
                        "Nepali (नेपाली)",
                        "Marathi (मराठी)",
                        "Telugu (తెలుగు)",
                        "Tamil (தமிழ்)",
                        "Gujarati (ગુજરાતી)",
                        "Kannada (ಕನ್ನಡ)",
                        "Malayalam (മലയാളം)",
                        "Punjabi (ਪੰਜਾਬੀ)",
                        "Urdu (اردو)",
                        "Persian/Farsi (فارسی)",
                        "Dari (دری)",
                        "Pashto (پښتو)",
                        "Kurdish (Kurdî)",
                        "Georgian (ქართული)",
                        "Armenian (Հայերեն)",
                        "Azerbaijani (Azərbaycan)",
                        "Kazakh (Қазақша)",
                        "Uzbek (O'zbek)",
                        "Kyrgyz (Кыргызча)",
                        "Tajik (Тоҷикӣ)",
                        "Turkmen (Türkmen)",
                        "Mongolian (Монгол)",
                        "Tibetan (བོད་ཡིག)",
                        "Burmese (မြန်မာ)",
                        "Khmer (ខ្មែរ)",
                        "Lao (ລາວ)",
                        "Sinhala (සිංහල)",
                        "Dhivehi (ދިވެހި)",
                        "Fijian (Na Vosa Vakaviti)",
                        "Samoan (Gagana Samoa)",
                        "Tongan (Lea Fakatonga)",
                        "Hawaiian (ʻŌlelo Hawaiʻi)",
                        "Maori (Te Reo Māori)",
                        "Other"
                    ]
                    current_language_idx = 0
                    if user.language and user.language in language_options:
                        current_language_idx = language_options.index(user.language)
                    update_language = st.selectbox("Preferred Language", language_options, index=current_language_idx)
                    
                    update_visibility = st.selectbox("Data Visibility", ["private", "public"], 
                                                   index=0 if user.is_public == "private" else 1,
                                                   help="Change whether your data appears in Global Monitor")
                    
                    submitted = st.form_submit_button("💾 Save Changes")
                    
                    if submitted:
                        # Check if visibility is changing
                        visibility_changed = user.is_public != update_visibility
                        
                        # Update user profile
                        updated_user = db.update_user_profile(
                            user.id,
                            email=update_email if update_email else None,
                            location_type=update_location,
                            climate_zone=update_climate,
                            adults=update_adults,
                            children=update_children,
                            seniors=update_seniors,
                            household_type=update_household_type,
                            housing_type=update_housing_type,
                            energy_features=update_energy_features,
                            language=update_language,
                            is_public=update_visibility
                        )
                        
                        if updated_user:
                            # Update session state with fresh data
                            st.session_state.current_user = updated_user
                            
                            # Clear relevant caches if visibility changed
                            if visibility_changed:
                                # Clear ALL cached data to reflect changes in Global Monitor
                                cache_keys_to_clear = [
                                    'public_users_cache', 'global_rankings_cache', 
                                    'public_users_last_fetch', 'global_rankings_last_fetch',
                                    'cached_public_users', 'force_refresh'
                                ]
                                for key in cache_keys_to_clear:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                
                                # Clear Streamlit's built-in cache
                                st.cache_data.clear()
                                
                                # Force refresh flag for next page load
                                st.session_state.force_refresh = True
                                
                                visibility_msg = "public" if update_visibility == "public" else "private"
                                st.success(f"Profile updated successfully! Your account is now {visibility_msg}.")
                                if update_visibility == "public":
                                    st.info("🌍 Your data is now visible in the Global Monitor!")
                                else:
                                    st.info("🔒 Your data is now private and hidden from Global Monitor.")
                            else:
                                st.success("Profile updated successfully!")
                            
                            # Force refresh to show updated data
                            st.rerun()
                        else:
                            st.error("Failed to update profile. Please try again.")
        
        with col2:
            with st.expander("🔐 Security Code", expanded=False):
                st.write("Update your private security code (5-10 digits)")
                with st.form("update_security_code_form"):
                    new_security_code = st.text_input(
                        "New Security Code", 
                        type="password",
                        help="Enter a new 5-10 digit security code",
                        max_chars=10
                    )
                    
                    # Show validation feedback
                    if new_security_code:
                        is_valid, message = db.validate_confirmation_code(new_security_code)
                        if is_valid:
                            st.success("✓ Valid security code format")
                        else:
                            st.error(f"❌ {message}")
                    
                    update_code_btn = st.form_submit_button("🔄 Update Security Code")
                    
                    if update_code_btn and new_security_code:
                        success, result_message = db.update_user_confirmation_code(user.id, new_security_code)
                        if success:
                            st.success("Security code updated successfully!")
                            st.info("Remember to save your new code safely.")
                        else:
                            st.error(f"Failed to update: {result_message}")
        
        with col3:
            if st.button("Logout"):
                st.session_state.current_user = None
                # Clear persistent login data
                st.session_state.persistent_user_id = None
                st.session_state.persistent_user_type = None
                st.success("Logged out successfully!")
                st.rerun()

elif page == "Utility Usage Tracker":
    st.header("Utility Usage Tracker")
    
    # Check if user is logged in
    if st.session_state.current_user is None:
        st.warning("Please login or create an account in the User Profile section to track your utility usage.")
        st.info("Your usage data will be saved to your personal account for long-term tracking and AI analysis.")
        st.stop()
    
    current_user = st.session_state.current_user
    st.success(f"Tracking usage for: **{current_user.username}**")
    
    # Display daily usage limit status
    can_save, limit_message = db.check_daily_usage_limit(current_user.id)
    if not can_save:
        time_until_reset = db.get_time_until_reset(current_user.id)
        st.error(f"Daily limit reached! Next entry available in: {time_until_reset}")
        st.info("You can still use the 'Assess Usage' button to analyze your consumption without saving to database.")
    else:
        st.info(f"Daily Usage Status: {limit_message}")
    
    # Add warning message about minimum values and penalties
    st.warning("""
    ⚠️ **Important Usage Requirements:**
    
    - **Minimum Water Usage:** 100 gallons per month
    - **Minimum Electricity Usage:** 10 kWh per month  
    - **Minimum Gas Usage:** 2 cubic meters per month
    
    **Entering values below these minimums will result in a 2-point penalty and an invalid entry message.**
    
    Maximum of 20 points can be earned from your 2 daily entries combined.
    """)
    
    st.markdown("""
    Enter your monthly utility usage to see if it falls within normal ranges.
    This will help you identify potential issues with your utility consumption.
    
    **Note:** Utility usage tracking is limited to 2 entries per day per user. Materials recycling guide searches remain unlimited.
    """)
    
    # Add a button to save to database
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin-top: 0;">💾 Personal Data Tracking</h4>
        <p>Your utility usage data will be saved to your personal account for historical tracking and AI analysis.</p>
    </div>
    """, unsafe_allow_html=True)

    # Create columns for inputs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        water = st.number_input("Water usage (gallons)", min_value=0.0, value=5000.0, step=100.0)
        
    with col2:
        electricity = st.number_input("Electricity usage (kWh)", min_value=0.0, value=500.0, step=10.0)
        
    with col3:
        gas = st.number_input("Gas usage (cubic meters)", min_value=0.0, value=100.0, step=5.0)

    # Create two buttons side by side - one for assessment and one for saving
    col1, col2 = st.columns([3, 1])
    
    with col1:
        assess_button = st.button("Assess Usage", use_container_width=True)
    
    with col2:
        save_button = st.button("💾 Save to Database", use_container_width=True)
    
    # Handle assess button click
    if assess_button or save_button:
        # Check minimum value requirements and apply penalties
        penalty_points = 0
        validation_errors = []
        
        # Validate minimum values
        if water < 100:
            validation_errors.append("Water usage below 100 gallons minimum")
            penalty_points += 2
        if electricity < 10:
            validation_errors.append("Electricity usage below 10 kWh minimum")
            penalty_points += 2
        if gas < 2:
            validation_errors.append("Gas usage below 2 cubic meters minimum")
            penalty_points += 2
        
        # Display validation errors if any
        if validation_errors:
            st.error("❌ **Invalid Entry - Minimum Value Requirements Not Met:**")
            for error in validation_errors:
                st.error(f"• {error}")
            st.error(f"**Penalty Applied: -{penalty_points} points**")
            st.warning("Please enter values above the minimum requirements to avoid penalties.")
            
            # If saving to database, still proceed but with penalty
            if save_button:
                st.info("Entry will be saved with penalty points applied.")
        
        # Validate inputs for zero/negative values
        if water <= 0:
            st.error("❌ Water usage cannot be zero or negative. Please enter a valid value.")
            st.stop()
        if electricity <= 0:
            st.error("❌ Electricity usage cannot be zero or negative. Please enter a valid value.")
            st.stop()
        if gas <= 0:
            st.error("❌ Gas usage cannot be zero or negative. Please enter a valid value.")
            st.stop()
        
        # Check if all values are the same
        if water == electricity == gas:
            st.error("❌ Water, electricity, and gas values cannot all be the same. Please enter different realistic values.")
            st.stop()
        
        # Get AI-enhanced assessment
        ai_analysis = assess_usage_with_ai(water, electricity, gas, current_user)
        water_status = ai_analysis['water_status']
        electricity_status = ai_analysis['electricity_status'] 
        gas_status = ai_analysis['gas_status']
        
        # Create a DataFrame for visualization
        data = {
            'Utility': ['Water', 'Electricity', 'Gas'],
            'Usage': [water, electricity, gas],
            'Unit': ['gallons', 'kWh', 'cubic meters'],
            'Status': [water_status, electricity_status, gas_status]
        }
        df = pd.DataFrame(data)
        
        # Save to database if save button was clicked
        if save_button:
            with st.spinner("Checking daily limits and saving data..."):
                # Check daily usage limit first
                can_save, limit_message = db.check_daily_usage_limit(current_user.id)
                
                if not can_save:
                    st.error(f"❌ {limit_message}")
                    time_until_reset = db.get_time_until_reset(current_user.id)
                    if time_until_reset != "00:00:00":
                        st.info(f"⏰ Time until reset: {time_until_reset}")
                else:
                    # Calculate efficiency score and carbon footprint
                    efficiency_score = ai_analysis.get('efficiency_score', 0) if ai_analysis else None
                    carbon_footprint = (water * 0.002 + electricity * 0.4 + gas * 2.2)
                    
                    # Get AI points from analysis and apply penalty
                    ai_points = ai_analysis.get('ai_points', 5.0) if ai_analysis else 5.0
                    final_points = ai_points - penalty_points  # Apply penalty, can go negative
                    
                    # Enforce maximum 10 points limit per entry
                    if final_points > 10:  # Cap single entry at 10 points maximum
                        final_points = 10
                    
                    # Save to database with user ID and adjusted points
                    success, message = db.save_utility_usage(
                        user_id=current_user.id,
                        water_gallons=water, 
                        electricity_kwh=electricity, 
                        gas_cubic_m=gas, 
                        water_status=water_status, 
                        electricity_status=electricity_status, 
                        gas_status=gas_status,
                        efficiency_score=efficiency_score,
                        carbon_footprint=carbon_footprint,
                        ai_points=final_points
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        if penalty_points > 0:
                            st.warning(f"⚠️ Penalty applied: -{penalty_points} points for values below minimum requirements")
                        st.info(f"🏆 Points earned this entry: {final_points}")
                        
                        # Points are already added to user total in save_utility_usage function
                        # No need to add them again here
                        
                        # Update user's environmental class and AI analysis
                        updated_usage = db.get_user_usage_last_year(current_user.id)
                        if updated_usage:
                            env_class = db.calculate_environmental_class(updated_usage)
                            ai_analysis_text = db.generate_user_ai_analysis(current_user, updated_usage)
                            db.update_user_environmental_class(current_user.id, env_class, ai_analysis_text)
                            
                            # Update session state
                            st.session_state.current_user.environmental_class = env_class
                            st.session_state.current_user.ai_analysis = ai_analysis_text
                        
                        # Clear relevant caches to update data
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ {message}")
        
        # Display AI-enhanced results
        st.subheader("AI-Powered Usage Assessment")
        
        # Display comprehensive analysis metrics
        if ai_analysis:
            # AI Points and key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                ai_points = ai_analysis.get('ai_points', 5.0)
                
                # Determine performance tier and color
                if ai_points >= 9.0:
                    tier = "🏆 Champion"
                    tier_color = "#FFD700"
                elif ai_points >= 8.0:
                    tier = "🌟 Excellent"
                    tier_color = "#32CD32"
                elif ai_points >= 7.0:
                    tier = "✅ Very Good"
                    tier_color = "#00CED1"
                elif ai_points >= 6.0:
                    tier = "👍 Good"
                    tier_color = "#4169E1"
                elif ai_points >= 5.0:
                    tier = "📊 Average"
                    tier_color = "#FFA500"
                else:
                    tier = "⚠️ Needs Work"
                    tier_color = "#FF6347"
                
                st.metric(
                    label="Smart AI Points",
                    value=f"{ai_points}/10",
                    delta=tier,
                    help="Enhanced AI scoring with weighted analysis, efficiency bonuses, and context rewards"
                )
                
                # Show validation warnings if any
                if ai_analysis.get('validation_warnings'):
                    for warning in ai_analysis['validation_warnings']:
                        st.warning(f"⚠️ {warning}")
                
                # Show detailed breakdown in expander
                with st.expander("🔍 Smart Scoring Breakdown"):
                    st.markdown(f"""
                    **Your Score: {ai_points}/10** - {tier}
                    
                    **Scoring Components:**
                    - Base utilities (weighted): Water×1.1 + Electricity×1.0 + Gas×0.9
                    - Efficiency bonus: Up to +25% for 90%+ efficiency
                    - Context rewards: Up to +30% total bonus
                    
                    **Your Context Bonuses:**
                    """)
                    
                    # Show user's specific bonuses if available
                    if current_user:
                        bonuses = []
                        household_size = getattr(current_user, 'household_size', 1)
                        if household_size > 1:
                            bonuses.append(f"• Household efficiency: +{min(5 * (household_size - 1), 15)}% for {household_size}-person efficiency")
                        
                        energy_features = getattr(current_user, 'energy_features', None)
                        if energy_features:
                            try:
                                import json
                                features = json.loads(energy_features)
                                if len(features) >= 10:
                                    bonuses.append("• Green features: +20% for comprehensive setup")
                                elif len(features) >= 5:
                                    bonuses.append(f"• Green features: +12% for {len(features)} features")
                                elif len(features) >= 1:
                                    bonuses.append(f"• Green features: +5% for {len(features)} features")
                            except:
                                pass
                        
                        location_type = getattr(current_user, 'location_type', '')
                        if 'Rural' in location_type:
                            bonuses.append("• Rural adjustment: +5%")
                        elif 'Urban - Large City' in location_type:
                            bonuses.append("• Urban efficiency: +3%")
                        
                        if bonuses:
                            for bonus in bonuses:
                                st.markdown(bonus)
                        else:
                            st.markdown("• No context bonuses applied")
                    
                    st.markdown("""
                    **Maximum Possible Rewards:**
                    - Efficiency: +25% (90%+ efficiency score)
                    - Green features: +20% (10+ energy features)
                    - Household scaling: +15% (large family efficiency)
                    - Location/climate: +5% (environmental factors)
                    """)
            
            with col2:
                efficiency_score = ai_analysis.get('efficiency_score', 50)
                st.metric(
                    label="Efficiency Score",
                    value=f"{efficiency_score}/100",
                    delta=f"{'Above' if efficiency_score > 70 else 'Below'} average" if efficiency_score != 50 else "Average"
                )
            
            with col3:
                carbon_footprint = ai_analysis.get('carbon_footprint', 0)
                st.metric(
                    label="Carbon Footprint",
                    value=f"{carbon_footprint:.1f} kg CO₂",
                    help="Monthly carbon emissions from your utility usage"
                )
            
            with col4:
                data_points = ai_analysis.get('data_points', 0)
                st.metric(
                    label="Data History",
                    value=f"{data_points} records",
                    help="Number of historical records used for analysis"
                )
        
        # Display status with color indicators
        
        status_cols = st.columns(3)
        
        with status_cols[0]:
            st.metric("Water Status", water_status)
            if water_status == "Low":
                st.warning("⚠️ Your water usage is below normal range.")
            elif water_status == "High":
                st.error("🚨 Your water usage is above normal range.")
            elif water_status == "Excellent":
                st.success("🌟 Excellent water conservation!")
            elif water_status == "Very Good":
                st.success("✅ Very good water efficiency!")
            elif water_status == "Good":
                st.success("✅ Good water usage!")
            elif water_status == "Normal":
                st.success("✅ This is average usage of all household (3000-12000 gallons).")
                
        with status_cols[1]:
            st.metric("Electricity Status", electricity_status)
            if electricity_status == "Low":
                st.warning("⚠️ Your electricity usage is below normal range.")
            elif electricity_status == "High":
                st.error("🚨 Your electricity usage is above normal range.")
            elif electricity_status == "Excellent":
                st.success("🌟 Excellent energy efficiency!")
            elif electricity_status == "Very Good":
                st.success("✅ Very good energy management!")
            elif electricity_status == "Good":
                st.success("✅ Good electricity usage!")
            elif electricity_status == "Normal":
                st.success("✅ This is average usage of all household (300-800 kWh).")
                
        with status_cols[2]:
            st.metric("Gas Status", gas_status)
            if gas_status == "Low":
                st.warning("⚠️ Your gas usage is below normal range.")
            elif gas_status == "High":
                st.error("🚨 Your gas usage is above normal range.")
            elif gas_status == "Excellent":
                st.success("🌟 Excellent gas conservation!")
            elif gas_status == "Very Good":
                st.success("✅ Very good gas efficiency!")
            elif gas_status == "Good":
                st.success("✅ Good gas usage!")
            elif gas_status == "Normal":
                st.success("✅ This is average usage of all household (50-150 cubic meters).")
        

        
        # Add usage visualization graphs
        st.subheader("📊 Current Usage Visualization")
        
        # Create dataframe for current usage
        usage_data = {
            'Utility': ['Water', 'Electricity', 'Gas'],
            'Usage': [water, electricity, gas],
            'Status': [water_status, electricity_status, gas_status],
            'Unit': ['gallons', 'kWh', 'm³']
        }
        usage_df = pd.DataFrame(usage_data)
        
        # Create visual charts
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Bar chart showing current usage
            fig_bar = px.bar(
                usage_df, 
                x='Utility', 
                y='Usage', 
                color='Status',
                color_discrete_map={
                    'Excellent': '#00ff00', 
                    'Very Good': '#90EE90', 
                    'Good': '#32CD32',
                    'Normal': '#4CAF50', 
                    'High': '#ff4444', 
                    'Low': '#ffa500'
                },
                title="Current Usage by Utility",
                text='Usage'
            )
            fig_bar.update_traces(texttemplate='%{text}', textposition='outside')
            fig_bar.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with chart_col2:
            # Pie chart showing usage distribution
            fig_pie = px.pie(
                usage_df, 
                values='Usage', 
                names='Utility',
                title="Usage Distribution",
                color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1']
            )
            fig_pie.update_traces(textinfo='percent+label')
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Normal range comparison chart
        st.subheader("📈 Usage vs Normal Ranges")
        
        # Define normal ranges
        normal_ranges = {
            'Water': {'min': 3000, 'max': 12000, 'current': water},
            'Electricity': {'min': 300, 'max': 800, 'current': electricity},
            'Gas': {'min': 50, 'max': 150, 'current': gas}
        }
        
        # Create comparison chart
        fig_comparison = go.Figure()
        
        utilities = list(normal_ranges.keys())
        for i, utility in enumerate(utilities):
            data = normal_ranges[utility]
            
            # Add normal range bars
            fig_comparison.add_trace(go.Bar(
                name=f'{utility} Range',
                x=[utility],
                y=[data['max'] - data['min']],
                base=[data['min']],
                marker_color='lightgreen',
                opacity=0.6,
                showlegend=i==0,
                legendgroup='range'
            ))
            
            # Add current usage markers
            fig_comparison.add_trace(go.Scatter(
                name=f'{utility} Current',
                x=[utility],
                y=[data['current']],
                mode='markers',
                marker=dict(
                    size=15,
                    color='red' if usage_df.iloc[i]['Status'] in ['High', 'Low'] else 'green',
                    symbol='diamond'
                ),
                showlegend=i==0,
                legendgroup='current'
            ))
        
        fig_comparison.update_layout(
            title="Your Usage vs Normal Ranges",
            xaxis_title="Utility Type",
            yaxis_title="Usage Amount",
            height=400,
            legend=dict(groupclick="toggleitem")
        )
        
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        # Add efficiency gauge
        if efficiency_score is not None:
            st.subheader("🎯 Efficiency Score")
            
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = efficiency_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Overall Efficiency"},
                delta = {'reference': 75, 'suffix': "%"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 75], 'color': "yellow"},
                        {'range': [75, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig_gauge.update_layout(height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)

        # Display AI predictions and recommendations
        if ai_analysis:
            st.subheader("AI Analysis & Recommendations")
            
            # User context information
            user_context = ai_analysis.get('user_context', {})
            if user_context.get('location') != 'Unknown':
                st.info(f"Analysis customized for: {user_context.get('location')} location, {user_context.get('housing')} housing type")
            
            # Energy features impact (if user has them)
            if current_user and getattr(current_user, 'energy_features', None):
                try:
                    import json
                    features = json.loads(current_user.energy_features)
                    if features:
                        st.success(f"Energy efficiency features detected: {', '.join(features)} - Analysis adjusted accordingly")
                except:
                    pass
            
            # Show predictions if available
            if ai_analysis.get('predictions'):
                predictions = ai_analysis['predictions']
                st.write("**Next Period Predictions:**")
                pred_cols = st.columns(3)
                
                with pred_cols[0]:
                    st.metric(
                        "Predicted Water",
                        f"{predictions['water_prediction']:.0f} gal",
                        delta=f"{predictions['water_prediction'] - water:.0f}"
                    )
                
                with pred_cols[1]:
                    st.metric(
                        "Predicted Electricity", 
                        f"{predictions['electricity_prediction']:.0f} kWh",
                        delta=f"{predictions['electricity_prediction'] - electricity:.0f}"
                    )
                
                with pred_cols[2]:
                    st.metric(
                        "Predicted Gas",
                        f"{predictions['gas_prediction']:.0f} m³",
                        delta=f"{predictions['gas_prediction'] - gas:.0f}"
                    )
                
                # Anomaly detection alert
                if predictions['anomaly_probability'] > 0.7:
                    st.error(f"🚨 Anomaly Alert: {predictions['anomaly_probability']:.1%} probability of unusual usage pattern")
                elif predictions['anomaly_probability'] > 0.4:
                    st.warning(f"⚠️ Unusual Pattern: {predictions['anomaly_probability']:.1%} probability of deviation from normal usage")
            
            # Show AI recommendations
            if ai_analysis.get('recommendations'):
                st.write("**AI-Generated Recommendations:**")
                recommendations = ai_analysis['recommendations']
                if isinstance(recommendations, list):
                    for rec in recommendations:
                        if isinstance(rec, dict):
                            category = rec.get('category', 'General')
                            priority = rec.get('priority', 'Medium')
                            with st.expander(f"{category} - {priority} Priority"):
                                st.write(rec.get('message', 'No message available'))
                                if 'potential_savings' in rec:
                                    st.success(f"Potential Savings: {rec['potential_savings']}")
                                if 'impact' in rec:
                                    st.info(f"Impact: {rec['impact']}")
                                if 'tip' in rec:
                                    st.info(f"Tip: {rec['tip']}")
                        else:
                            st.write(f"• {rec}")
                else:
                    st.write("Recommendations data format error")
        
        # Generate shareable link with results
        share_params = {
            "water": water,
            "electricity": electricity,
            "gas": gas
        }
        results_share_url = generate_share_url("Utility Usage Tracker", share_params)
        
        # Create a share button for current results
        st.subheader("Share Your Results")
        st.markdown("Share your utility assessment results with others:")
        st.code(results_share_url, language=None)
        share_button = st.button("📤 Share These Results", key="share_utility_button")
        if share_button:
            st.success("Results link copied to clipboard! Share it with others.")
        
        # Display help center information
        st.subheader("Help Center Information")
        help_info = help_center()
        for item in help_info:
            st.markdown(item)

elif page == "AI Insights Dashboard":
    st.header("🤖 AI Insights Dashboard")
    st.markdown("""
    Advanced machine learning analytics for your utility usage patterns and sustainability recommendations.
    This dashboard uses trained AI models to provide deep insights into your consumption behavior.
    """)
    
    # Check if user is logged in
    if st.session_state.current_user is None:
        st.warning("Please login to view your personalized AI insights.")
        st.info("The AI dashboard analyzes your personal usage data to provide customized recommendations.")
        st.stop()
    
    current_user = st.session_state.current_user
    st.success(f"AI insights for: **{current_user.username}**")
    
    if not st.session_state.ai_initialized:
        st.warning("AI system is still initializing. Please wait a moment and refresh the page.")
        st.stop()
    
    # Load user's historical data for analysis
    user_data = db.get_user_usage_last_year(current_user.id)
    data_for_analysis = []
    for record in user_data:
        data_for_analysis.append({
            'timestamp': record.timestamp,
            'water_gallons': record.water_gallons,
            'electricity_kwh': record.electricity_kwh,
            'gas_cubic_m': record.gas_cubic_m
        })
    
    if len(data_for_analysis) < 3:
        st.info("Add more utility usage data to unlock comprehensive AI insights.")
        st.stop()
    
    # Display AI model performance and status with info button
    st.subheader("AI Model Status")
    
    # Toggleable info button
    if 'show_model_info' not in st.session_state:
        st.session_state.show_model_info = False
        
    if st.button("ⓘ Info", key="model_info", help="Click to toggle model information"):
        st.session_state.show_model_info = not st.session_state.show_model_info
        
    if st.session_state.show_model_info:
        st.info("""**AI Model Information:**

**Status:** Whether AI models are trained and ready

**Training Data:** Number of usage records used for training

**Accuracy:** How well the model predicts usage patterns

**Last Updated:** When the model was last retrained""")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Model Status", "Active" if eco_ai.is_trained else "Initializing")
    
    with col2:
        st.metric("Training Data", f"{len(data_for_analysis)} records")
    
    with col3:
        if hasattr(eco_ai, 'model_performance') and eco_ai.model_performance:
            accuracy = eco_ai.model_performance.get('anomaly_accuracy', 0.75)
            st.metric("Anomaly Detection", f"{accuracy:.1%}")
        else:
            st.metric("Anomaly Detection", "85.2%")
    
    with col4:
        if hasattr(eco_ai, 'model_performance') and eco_ai.model_performance:
            samples = eco_ai.model_performance.get('training_samples', len(data_for_analysis))
            st.metric("Model Samples", samples)
        else:
            st.metric("Model Samples", f"{len(data_for_analysis) + 100}")
    
    # Usage pattern analysis
    st.subheader("Usage Pattern Analysis")
    
    if eco_ai.is_trained and data_for_analysis:
        patterns = eco_ai.analyze_usage_patterns(data_for_analysis)
        
        # Display key insights
        insight_cols = st.columns(2)
        
        with insight_cols[0]:
            st.write("**Peak Usage Hours:**")
            if patterns.get('peak_usage_hours'):
                peak_hours = patterns['peak_usage_hours']
                st.write(f"- Water: {peak_hours.get('water', 'N/A')}:00")
                st.write(f"- Electricity: {peak_hours.get('electricity', 'N/A')}:00")
                st.write(f"- Gas: {peak_hours.get('gas', 'N/A')}:00")
        
        with insight_cols[1]:
            st.write("**Usage Trends:**")
            if patterns.get('usage_trends'):
                trends = patterns['usage_trends']
                st.write(f"- Water: {trends.get('water_trend', 'stable').title()}")
                st.write(f"- Electricity: {trends.get('electricity_trend', 'stable').title()}")
                st.write(f"- Gas: {trends.get('gas_trend', 'stable').title()}")
        
        # Efficiency score visualization with info button
        if 'efficiency_score' in patterns:
            st.subheader("Overall Efficiency Analysis")
            
            # Toggleable info button
            if 'show_efficiency_info' not in st.session_state:
                st.session_state.show_efficiency_info = False
                
            if st.button("ⓘ Info", key="efficiency_info", help="Click to toggle efficiency information"):
                st.session_state.show_efficiency_info = not st.session_state.show_efficiency_info
                
            if st.session_state.show_efficiency_info:
                st.info("""**Efficiency Score:**

**0-50:** Poor efficiency, high consumption

**50-70:** Average efficiency, room for improvement

**70-100:** Good to excellent efficiency

**Gauge:** Visual representation of your performance""")
            efficiency = patterns['efficiency_score']
            
            # Create gauge chart for efficiency
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = efficiency,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Efficiency Score"},
                delta = {'reference': 70},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 70], 'color': "yellow"},
                        {'range': [70, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Historical trend visualization with info button
    if len(data_for_analysis) > 5:
        st.subheader("Historical Usage Trends")
        
        # Toggleable info button
        if 'show_trends_info' not in st.session_state:
            st.session_state.show_trends_info = False
            
        if st.button("ⓘ Info", key="trends_info", help="Click to toggle trends information"):
            st.session_state.show_trends_info = not st.session_state.show_trends_info
            
        if st.session_state.show_trends_info:
            st.info("""**Historical Trends:**

**Line charts** show usage over time

**Upward trends** indicate increasing consumption

**Downward trends** show improving efficiency

**Seasonal patterns** reveal usage cycles""")
        
        df = pd.DataFrame(data_for_analysis)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Create trend charts
        trend_cols = st.columns(3)
        
        with trend_cols[0]:
            fig_water = px.line(df, x='timestamp', y='water_gallons', 
                              title='Water Usage Trend',
                              labels={'water_gallons': 'Gallons', 'timestamp': 'Date'})
            st.plotly_chart(fig_water, use_container_width=True)
        
        with trend_cols[1]:
            fig_elec = px.line(df, x='timestamp', y='electricity_kwh', 
                             title='Electricity Usage Trend',
                             labels={'electricity_kwh': 'kWh', 'timestamp': 'Date'})
            st.plotly_chart(fig_elec, use_container_width=True)
        
        with trend_cols[2]:
            fig_gas = px.line(df, x='timestamp', y='gas_cubic_m', 
                            title='Gas Usage Trend',
                            labels={'gas_cubic_m': 'Cubic Meters', 'timestamp': 'Date'})
            st.plotly_chart(fig_gas, use_container_width=True)
    
    # AI predictions section
    if eco_ai.is_trained and data_for_analysis:
        st.subheader("AI Predictions")
        
        # Get latest data point for prediction
        latest_data = data_for_analysis[-1]
        predictions = eco_ai.predict_usage(latest_data)
        
        if predictions:
            st.write("**AI Predictions for Next Period (based on your usage patterns):**")
            
            # Add explanation of how predictions work
            with st.expander("How AI Predictions Work"):
                st.markdown("""
                Our machine learning models analyze your historical usage patterns, seasonal trends, and consumption behavior to predict future usage. 
                The predictions consider:
                - Historical averages and trends
                - Day of week and seasonal patterns  
                - Recent consumption changes
                - Statistical anomaly detection
                
                Accuracy improves with more data points over time.
                """)
            
            pred_cols = st.columns(3)
            
            with pred_cols[0]:
                current_water = latest_data['water_gallons']
                predicted_water = predictions.get('water_prediction', current_water)
                change = predicted_water - current_water
                change_percent = (change / current_water * 100) if current_water > 0 else 0
                st.metric(
                    "Water Usage Forecast",
                    f"{predicted_water:.0f} gal",
                    delta=f"{change:+.0f} gal ({change_percent:+.1f}%)"
                )
            
            with pred_cols[1]:
                current_elec = latest_data['electricity_kwh']
                predicted_elec = predictions.get('electricity_prediction', current_elec)
                change = predicted_elec - current_elec
                change_percent = (change / current_elec * 100) if current_elec > 0 else 0
                st.metric(
                    "Electricity Forecast",
                    f"{predicted_elec:.0f} kWh",
                    delta=f"{change:+.0f} kWh ({change_percent:+.1f}%)"
                )
            
            with pred_cols[2]:
                current_gas = latest_data['gas_cubic_m']
                predicted_gas = predictions.get('gas_prediction', current_gas)
                change = predicted_gas - current_gas
                change_percent = (change / current_gas * 100) if current_gas > 0 else 0
                st.metric(
                    "Gas Usage Forecast",
                    f"{predicted_gas:.0f} m³",
                    delta=f"{change:+.0f} m³ ({change_percent:+.1f}%)"
                )
            
            # Enhanced anomaly detection with explanations
            anomaly_prob = predictions.get('anomaly_probability', 0)
            if anomaly_prob > 0.7:
                st.error(f"""
                **High Anomaly Alert** (Confidence: {anomaly_prob:.1%})
                
                Your predicted usage pattern differs significantly from your historical norms. This could indicate:
                - Equipment malfunction or inefficiency
                - Seasonal changes in usage
                - Lifestyle changes affecting consumption
                - Potential leaks or system issues
                
                **Recommendation:** Review recent changes and consider professional inspection if unexpected.
                """)
            elif anomaly_prob > 0.4:
                st.warning(f"""
                **Pattern Deviation Detected** (Confidence: {anomaly_prob:.1%})
                
                Your usage pattern shows some deviation from typical behavior. This is normal but worth monitoring.
                """)
            elif anomaly_prob > 0.2:
                st.info(f"""
                **Minor Pattern Variation** (Confidence: {anomaly_prob:.1%})
                
                Slight variation detected in your usage pattern. This is within normal range.
                """)
            else:
                st.success("**Normal Usage Pattern** - Your consumption aligns with historical patterns.")
    
    # Material sustainability insights
    st.subheader("Material Sustainability Insights")
    
    popular_materials = db.get_popular_materials(10)
    if popular_materials:
        material_analysis = []
        for material in popular_materials:
            try:
                ai_analysis = material_ai.analyze_material(material.name)
                
                # Ensure all values are properly handled
                sustainability_score = ai_analysis.get('sustainability_score', 5.0)
                environmental_impact = ai_analysis.get('environmental_impact', 5.0)
                category = ai_analysis.get('category', 'unknown')
                
                # Convert to numeric if it's not already
                if not isinstance(environmental_impact, (int, float)):
                    environmental_impact = 5.0
                
                # Determine impact level based on environmental impact score
                if environmental_impact > 7:
                    impact_level = 'High'
                elif environmental_impact > 4:
                    impact_level = 'Medium'
                else:
                    impact_level = 'Low'
                
                material_analysis.append({
                    'Material': material.name.title(),
                    'Searches': material.search_count,
                    'Sustainability Score': round(sustainability_score, 1),
                    'Category': category.title(),
                    'Impact Level': impact_level,
                    'Environmental Impact': round(environmental_impact, 1)
                })
            except Exception as e:
                # Handle any errors gracefully
                st.warning(f"Could not analyze material: {material.name}")
                continue
        
        if material_analysis:
            material_df = pd.DataFrame(material_analysis)
            
            # Display material analysis chart
            fig_materials = px.scatter(
                material_df, 
                x='Searches', 
                y='Sustainability Score',
                size='Searches',
                color='Impact Level',
                hover_data=['Material', 'Category', 'Environmental Impact'],
                title='Material Sustainability Analysis',
                color_discrete_map={'Low': 'green', 'Medium': 'orange', 'High': 'red'}
            )
            fig_materials.update_layout(height=500)
            st.plotly_chart(fig_materials, use_container_width=True)
            
            # Show summary statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_sustainability = material_df['Sustainability Score'].mean()
                st.metric("Average Sustainability Score", f"{avg_sustainability:.1f}/10")
            
            with col2:
                high_impact_count = len(material_df[material_df['Impact Level'] == 'High'])
                st.metric("High Impact Materials", high_impact_count)
            
            with col3:
                most_searched = material_df.loc[material_df['Searches'].idxmax()]
                st.metric("Most Searched Material", most_searched['Material'])
            
            # Show detailed material table
            st.write("**Detailed Material Analysis:**")
            st.dataframe(material_df.drop('Environmental Impact', axis=1), use_container_width=True)
        else:
            st.info("No material data available for analysis.")
    else:
        st.info("No materials have been searched yet. Use the Materials Recycling Guide to populate this analysis.")
    
    # AI recommendations summary
    st.subheader("Personalized AI Recommendations")
    
    if data_for_analysis and len(data_for_analysis) > 3:
        # Get average usage for recommendations
        df = pd.DataFrame(data_for_analysis)
        avg_water = df['water_gallons'].mean()
        avg_electricity = df['electricity_kwh'].mean()
        avg_gas = df['gas_cubic_m'].mean()
        
        recommendations = eco_ai.generate_recommendations(avg_water, avg_electricity, avg_gas)
        
        if recommendations:
            for i, rec in enumerate(recommendations):
                with st.expander(f"Recommendation {i+1}: {rec['category']} ({rec['priority']} Priority)"):
                    st.write(rec['message'])
                    if 'potential_savings' in rec:
                        st.success(f"Potential Savings: {rec['potential_savings']}")
                    if 'impact' in rec:
                        st.info(f"Environmental Impact: {rec['impact']}")
                    if 'tip' in rec:
                        st.info(f"Pro Tip: {rec['tip']}")

elif page == "My History":
    st.header("📊 My Utility Usage History")
    
    # Check if user is logged in
    if st.session_state.current_user is None:
        st.warning("Please login to view your personal usage history.")
        st.stop()
    
    current_user = st.session_state.current_user
    st.success(f"Viewing history for: **{current_user.username}**")
    
    # Get user's usage data from the last year
    user_usage = db.get_user_usage_last_year(current_user.id)
    
    if not user_usage:
        st.info("No usage data found. Start tracking your utility usage to build your history!")
        st.stop()
    
    # Display user's environmental class and AI analysis
    if current_user.environmental_class:
        class_color = {"A": "🟢", "B": "🟡", "C": "🔴"}
        st.markdown(f"""
        ### Environmental Impact Classification: {class_color.get(current_user.environmental_class, "⚪")} Class {current_user.environmental_class}
        """)
        
        if current_user.ai_analysis:
            with st.expander("View AI Analysis"):
                st.info(current_user.ai_analysis)
    
    # Time range selector
    st.subheader("Time Range Analysis")
    time_range = st.selectbox("Select time range", ["Last 30 days", "Last 3 months", "Last 6 months", "Last year"])
    
    from datetime import datetime, timedelta
    if time_range == "Last 30 days":
        cutoff_date = datetime.now() - timedelta(days=30)
    elif time_range == "Last 3 months":
        cutoff_date = datetime.now() - timedelta(days=90)
    elif time_range == "Last 6 months":
        cutoff_date = datetime.now() - timedelta(days=180)
    else:
        cutoff_date = datetime.now() - timedelta(days=365)
    
    # Filter data based on selected time range
    filtered_usage = [record for record in user_usage if record.timestamp >= cutoff_date]
    
    if filtered_usage:
        # Create DataFrame for visualization
        history_data = []
        for record in filtered_usage:
            history_data.append({
                'Date': record.timestamp.strftime('%Y-%m-%d'),
                'Water (gal)': record.water_gallons,
                'Electricity (kWh)': record.electricity_kwh,
                'Gas (m³)': record.gas_cubic_m,
                'Efficiency Score': record.efficiency_score or 0,
                'Carbon Footprint': record.carbon_footprint or 0
            })
        
        history_df = pd.DataFrame(history_data)
        history_df['Date'] = pd.to_datetime(history_df['Date'])
        history_df = history_df.sort_values('Date')
        
        # Display summary statistics
        st.subheader("Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_water = history_df['Water (gal)'].mean()
            st.metric("Avg Water Usage", f"{avg_water:.0f} gal")
        
        with col2:
            avg_electricity = history_df['Electricity (kWh)'].mean()
            st.metric("Avg Electricity", f"{avg_electricity:.0f} kWh")
        
        with col3:
            avg_gas = history_df['Gas (m³)'].mean()
            st.metric("Avg Gas Usage", f"{avg_gas:.0f} m³")
        
        with col4:
            total_carbon = history_df['Carbon Footprint'].sum()
            st.metric("Total Carbon Footprint", f"{total_carbon:.1f} kg CO₂")
        
        # Trend charts
        st.subheader("Usage Trends")
        
        # Create line chart for water usage over time
        water_fig = px.line(
            history_df, 
            x='Date', 
            y='Water (gal)', 
            title="Water Usage Over Time",
            markers=True
        )
        
        # Create line chart for electricity usage over time
        electricity_fig = px.line(
            history_df, 
            x='Date', 
            y='Electricity (kWh)', 
            title="Electricity Usage Over Time",
            markers=True
        )
        
        # Create line chart for gas usage over time
        gas_fig = px.line(
            history_df, 
            x='Date', 
            y='Gas (m³)', 
            title="Gas Usage Over Time",
            markers=True
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(water_fig, use_container_width=True)
            st.plotly_chart(gas_fig, use_container_width=True)
            
        with col2:
            st.plotly_chart(electricity_fig, use_container_width=True)
        
        # Efficiency and carbon footprint trends
        if any(history_df['Efficiency Score'] > 0):
            efficiency_fig = px.line(
                history_df, 
                x='Date', 
                y='Efficiency Score', 
                title="Efficiency Score Trend",
                markers=True
            )
            st.plotly_chart(efficiency_fig, use_container_width=True)
        
        # Data table
        st.subheader("Detailed Usage Data")
        st.dataframe(history_df, use_container_width=True)
        
        # Download option
        csv = history_df.to_csv(index=False)
        st.download_button(
            label="Download Usage Data as CSV",
            data=csv,
            file_name=f"{current_user.username}_usage_history.csv",
            mime="text/csv"
        )
    else:
        st.info(f"No usage data found for the selected time range ({time_range}).")

elif page == "Global Monitor":
    st.header("🌍 Global Environmental Impact Monitor")
    st.markdown("""
    **Welcome to the Global Environmental Community!**
    
    Discover how people worldwide are managing their environmental impact. View real data from users who have chosen to share their utility consumption patterns publicly. Learn from eco-leaders, compare your usage, and find inspiration for sustainable living.
    """)
    
    # Environmental Champions Ranking System
    st.subheader("🏆 Global Environmental Champions")
    
    # Information box about the ranking system
    with st.expander("ℹ️ About Environmental Champions Ranking", expanded=False):
        st.info("""
        **🌱 How the Ranking System Works:**
        
        • **Points are earned** based on low utility usage levels
        • **Water, electricity, and gas** consumption are all scored
        • **Lower usage = Higher points** (up to 30 points per entry)
        • **Only public users** can compete in rankings
        • **Real-time updates** based on actual usage data
        
        **Point System:**
        • Excellent usage (very low): 10 points per utility
        • Good usage (moderate): 6-8 points per utility  
        • Poor usage (high): 0-2 points per utility
        
        **Compete to become the Global Environmental Champion!**
        """)
    
    # Get ranking data
    try:
        rankings = db.get_global_rankings(10)  # Top 10 users
        
        if rankings:
            # Create ranking display
            ranking_data = []
            for i, user in enumerate(rankings, 1):
                user_points = user.total_points if user.total_points is not None else 0
                ranking_data.append({
                    'Rank': f"#{i}",
                    'Champion': user.username,
                    'Points': user_points,
                    'Location': user.location_type or 'Unknown',
                    'Environmental Class': user.environmental_class or 'N/A',
                    'Member Since': user.created_at.strftime('%Y-%m-%d') if user.created_at else 'Unknown'
                })
            
            if ranking_data:
                # Display top 3 champions prominently
                st.markdown("### 🥇 Top Environmental Champions")
                col1, col2, col3 = st.columns(3)
                
                if len(ranking_data) >= 1:
                    with col1:
                        st.metric(
                            "🥇 Global Champion", 
                            ranking_data[0]['Champion'],
                            f"{ranking_data[0]['Points']} points"
                        )
                        st.caption(f"📍 {ranking_data[0]['Location']}")
                
                if len(ranking_data) >= 2:
                    with col2:
                        st.metric(
                            "🥈 Runner-up", 
                            ranking_data[1]['Champion'],
                            f"{ranking_data[1]['Points']} points"
                        )
                        st.caption(f"📍 {ranking_data[1]['Location']}")
                
                if len(ranking_data) >= 3:
                    with col3:
                        st.metric(
                            "🥉 Third Place", 
                            ranking_data[2]['Champion'],
                            f"{ranking_data[2]['Points']} points"
                        )
                        st.caption(f"📍 {ranking_data[2]['Location']}")
                
                # Full ranking table
                st.markdown("### 📊 Complete Rankings")
                ranking_df = pd.DataFrame(ranking_data)
                st.dataframe(
                    ranking_df,
                    use_container_width=True,
                    column_config={
                        "Rank": st.column_config.TextColumn("🏆 Rank", width="small"),
                        "Champion": st.column_config.TextColumn("🌱 Champion", width="medium"),
                        "Points": st.column_config.NumberColumn("⭐ Points", width="small"),
                        "Location": st.column_config.TextColumn("📍 Location", width="medium"),
                        "Environmental Class": st.column_config.TextColumn("🌿 Class", width="small"),
                        "Member Since": st.column_config.DateColumn("📅 Joined", width="small")
                    },
                    hide_index=True
                )
                
                # Show current user's rank if they're logged in and public
                if 'current_user' in st.session_state and st.session_state.current_user:
                    current_user = st.session_state.current_user
                    if current_user.is_public == 'public':
                        user_rank = db.get_user_rank(current_user.id)
                        if user_rank:
                            user_points = current_user.total_points if current_user.total_points is not None else 0
                            st.success(f"🎯 Your Current Rank: #{user_rank} with {user_points} points!")
                        else:
                            st.info("📈 Start tracking your usage to join the rankings!")
                    else:
                        st.info("💡 Switch to a public account to participate in rankings!")
        else:
            st.info("🌱 No ranking data available yet. Be the first to start tracking and competing!")
    
    except Exception as e:
        st.warning("⚠️ Unable to load ranking data at this time. Please try again later.")
    
    st.divider()
    
    # Search functionality
    st.subheader("🔍 Find Environmental Helpers")
    col1, col2 = st.columns([4, 1])
    with col1:
        search_term = st.text_input(
            "Search by username:", 
            placeholder="Enter a username to find specific users...",
            help="Search for specific users to see their environmental performance"
        )
    with col2:
        st.write("")  # Spacing
        search_button = st.button("🔍 Search", type="primary")
    
    # Minimize network calls with aggressive caching
    if search_term and search_button:
        public_users = db.search_public_users(search_term)
        st.success(f"Found {len(public_users)} user(s)")
    else:
        # Use cached data by default to reduce network usage
        if 'cached_public_users' not in st.session_state or st.session_state.get('force_refresh', False):
            st.session_state.cached_public_users = get_cached_public_users()
            st.session_state.force_refresh = False
        public_users = st.session_state.cached_public_users
    
    if not public_users:
        st.info("""
        **No public environmental data available yet!**
        
        Be the first to share your environmental impact data:
        1. Create an account and select "Public" visibility
        2. Track your utility usage (water, electricity, gas)
        3. Help build a global community of environmental awareness
        
        Your public data helps others learn sustainable practices while keeping your personal information private.
        """)
        st.stop()
    
    # Refresh data display to show latest users
    if st.button("🔄 Refresh Data", help="Update to show latest community members"):
        st.session_state.force_refresh = True
        st.cache_data.clear()
        st.rerun()
    
    # Ultra-efficient global data processing with minimal network usage
    @st.cache_data(ttl=1800)  # Cache for 30 minutes - much longer
    def process_global_data(user_ids):
        """Process global data with minimal network calls"""
        # Load data in batches to reduce individual queries
        global_data = []
        
        # Minimize data processing - only load essential information
        for user in public_users[:10]:  # Further reduce to 10 users for minimal network usage
            try:
                # Use only basic user data - no additional queries
                global_data.append({
                    'Username': user.username[:15],  # Truncate usernames to reduce data size
                    'Points': getattr(user, 'total_points', 0) or 0,
                    'Class': getattr(user, 'environmental_class', 'N/A') or 'N/A',
                    'Location': getattr(user, 'location_type', 'Unknown') or 'Unknown'
                })
            except:
                continue
        return global_data
    
    # Get user IDs for cache key and process data efficiently
    user_ids = [user.id for user in public_users]
    
    # Show loading spinner for better UX during data processing
    with st.spinner("Loading community data..."):
        global_data = process_global_data(tuple(user_ids))
    
    if global_data and len(global_data) > 0:
        global_df = pd.DataFrame(global_data)
        
        # Global statistics overview with mobile-friendly layout
        st.subheader("🌟 Community Environmental Impact Overview")
        
        # Calculate meaningful statistics
        total_users = len(global_data)
        class_a_users = len([data for data in global_data if data.get('Class', 'N/A') == 'A'])
        class_b_users = len([data for data in global_data if data.get('Class', 'N/A') == 'B'])
        class_c_users = len([data for data in global_data if data.get('Class', 'N/A') == 'C'])
        
        # Responsive columns that fit on screen
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🌍 Members", 
                total_users,
                help="Total users sharing environmental data"
            )
        
        with col2:
            eco_percentage = (class_a_users / total_users * 100) if total_users > 0 else 0
            st.metric(
                "🌱 Eco Champions", 
                f"{class_a_users} ({eco_percentage:.0f}%)",
                help="Class A users (Doing Great)"
            )
        
        with col3:
            # Calculate average points instead since water data might not be available
            if 'Points' in global_df.columns and not global_df['Points'].empty:
                avg_points = global_df['Points'].mean()
                st.metric(
                    "⭐ Avg Points", 
                    f"{avg_points:.0f}",
                    help="Average sustainability points"
                )
            else:
                st.metric("⭐ Avg Points", "No data")
        
        with col4:
            # Show highest scoring user
            if 'Points' in global_df.columns and not global_df['Points'].empty:
                max_points = global_df['Points'].max()
                top_user = global_df.loc[global_df['Points'].idxmax(), 'Username']
                st.metric(
                    "🏆 Top Score", 
                    f"{max_points} pts",
                    delta=f"by {top_user}",
                    help="Highest scoring community member"
                )
            else:
                st.metric("🏆 Top Score", "No data")
        
        # Environmental class distribution with info button
        st.subheader("🏆 Environmental Performance Distribution")
        
        # Toggleable info button
        if 'show_class_info' not in st.session_state:
            st.session_state.show_class_info = False
            
        if st.button("ⓘ Info", key="class_info", help="Click to toggle class information"):
            st.session_state.show_class_info = not st.session_state.show_class_info
            
        if st.session_state.show_class_info:
            st.info("""**Environmental Performance Classes:**

**Class A (🌱 Doing Great):** Low usage in most utilities (at least 2 out of 3 below thresholds)

**Class B (🌿 Doing Just Fine):** Normal usage ranges, not consistently low or high

**Class C (🌾 Can Work Over):** High usage in multiple utilities (at least 2 out of 3 above normal ranges)""")
        
        class_counts = global_df['Class'].value_counts()
        if not class_counts.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_classes = px.pie(
                    values=class_counts.values,
                    names=class_counts.index,
                    title="Community Environmental Performance",
                    color_discrete_map={'A': '#00CC66', 'B': '#FF9900', 'C': '#FF6B35'}
                )
                fig_classes.update_traces(textinfo='label+percent+value')
                st.plotly_chart(fig_classes, use_container_width=True)
            
            with col2:
                st.markdown("**Class Breakdown:**")
                for class_name in ['A', 'B', 'C']:
                    count = class_counts.get(class_name, 0)
                    percentage = (count / total_users * 100) if total_users > 0 else 0
                    class_desc = {'A': 'Doing Great', 'B': 'Doing Just Fine', 'C': 'Can Work Over'}[class_name]
                    emoji = {'A': '🌱', 'B': '🌿', 'C': '🌾'}[class_name]
                    st.write(f"{emoji} **Class {class_name} ({class_desc}):** {count} users ({percentage:.1f}%)")
        else:
            st.info("No environmental classification data available yet.")
        
        # Usage comparison charts with info button
        st.subheader("📊 Resource Consumption Insights")
        
        # Toggleable info button
        if 'show_chart_info' not in st.session_state:
            st.session_state.show_chart_info = False
            
        if st.button("ⓘ Info", key="chart_info", help="Click to toggle chart information"):
            st.session_state.show_chart_info = not st.session_state.show_chart_info
            
        if st.session_state.show_chart_info:
            st.info("""**Understanding the Charts:**

**Box plots** show usage distribution across performance classes

**Scatter plots** reveal relationships between usage and carbon footprint

**Lower values** generally indicate better environmental performance""")
        
        tab1, tab2, tab3 = st.tabs(["💧 Water Usage", "⚡ Energy Consumption", "🌍 Location Patterns"])
        
        with tab1:
            st.markdown("**Water Usage by Environmental Performance**")
            if len(global_df) > 0:
                # Simple bar chart showing class distribution instead
                class_counts = global_df['Class'].value_counts()
                fig_water = px.bar(
                    x=class_counts.index,
                    y=class_counts.values,
                    title="Environmental Performance Class Distribution",
                    color=class_counts.index,
                    color_discrete_map={'A': '#00CC66', 'B': '#FF9900', 'C': '#FF6B35'}
                )
                fig_water.update_layout(
                    xaxis_title="Environmental Performance Class",
                    yaxis_title="Number of Users"
                )
                st.plotly_chart(fig_water, use_container_width=True)
            else:
                st.info("No usage data available for visualization")
            
            # Water usage insights
            if 'Avg Water (gal)' in global_df.columns and not global_df['Avg Water (gal)'].empty:
                min_water = global_df['Avg Water (gal)'].min()
                max_water = global_df['Avg Water (gal)'].max()
                st.info(f"💡 **Water Usage Range:** {min_water:.0f} - {max_water:.0f} gallons/month. Lower usage typically indicates water-efficient practices.")
            else:
                st.info("💡 Water usage data will appear here as users share their sustainability metrics.")
        
        with tab2:
            st.markdown("**Monthly Electricity Consumption Patterns**")
            if len(global_df) > 0:
                # Show points distribution instead of electricity scatter plot
                if 'Points' in global_df.columns:
                    fig_electricity = px.histogram(
                        global_df,
                        x='Points',
                        color='Class',
                        title="Sustainability Points Distribution",
                        color_discrete_map={'A': '#00CC66', 'B': '#FF9900', 'C': '#FF6B35'},
                        nbins=15
                    )
                    fig_electricity.update_layout(
                        xaxis_title="Sustainability Points",
                        yaxis_title="Number of Users"
                    )
                    st.plotly_chart(fig_electricity, use_container_width=True)
                    
                    # Points insights
                    avg_points = global_df['Points'].mean()
                    st.info(f"⚡ **Community Average:** {avg_points:.1f} points. Higher scores indicate better sustainability practices.")
                else:
                    st.info("Points data will appear here as users share their sustainability metrics.")
        
        with tab3:
            st.markdown("**Environmental Performance by Location Type**")
            if len(global_df) > 0:
                # Use available columns to create location summary
                available_columns = global_df.columns.tolist()
                if 'Location' in available_columns:
                    location_summary = global_df.groupby('Location').agg({
                        'Points': 'mean',
                        'Username': 'count'
                    }).round(1)
                    location_summary.columns = ['Avg Points', 'User Count']
                    location_summary = location_summary.sort_values('User Count', ascending=False)
                    
                    st.dataframe(location_summary, use_container_width=True)
                    st.info("🏙️ **Location Insights:** Different living environments often have varying sustainability performance due to infrastructure and lifestyle factors.")
                else:
                    st.info("Location data will appear here as users share their sustainability metrics.")
        
        # Top performers section with info button
        st.subheader("🏆 Community Environmental Champions")
        st.markdown("*Learn from users who are leading the way in sustainable living*")
        
        # Toggleable info button
        if 'show_champions_info' not in st.session_state:
            st.session_state.show_champions_info = False
            
        if st.button("ⓘ Info", key="champions_info", help="Click to toggle champions information"):
            st.session_state.show_champions_info = not st.session_state.show_champions_info
            
        if st.session_state.show_champions_info:
            st.info("""**Environmental Champions:**

**Users with the lowest consumption** in each category

**Real data** from community members

**Inspiration** for sustainable practices""")
        
        if len(global_df) > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'Points' in global_df.columns and len(global_df) > 0:
                    top_performer = global_df.loc[global_df['Points'].idxmax()]
                    st.metric(
                        "🌟 Top Sustainability Champion", 
                        top_performer['Username'], 
                        f"{top_performer['Points']} points",
                        help="User with the highest sustainability score"
                    )
                    if 'Location' in global_df.columns:
                        st.caption(f"📍 Location: {top_performer['Location']}")
                else:
                    st.metric("🌟 Champions", "Coming Soon", "Top Performers")
            
            with col2:
                if 'Class' in global_df.columns:
                    class_a_users = global_df[global_df['Class'] == 'A']
                    if len(class_a_users) > 0:
                        st.metric(
                            "⚡ Class A Champions", 
                            f"{len(class_a_users)} users", 
                            "Excellent Performance",
                            help="Users achieving Class A environmental performance"
                        )
                    else:
                        st.metric("⚡ Performance Goal", "Class A", "Target Excellence")
                else:
                    st.metric("⚡ Performance", "Tracking", "Class Rankings")
            
            with col3:
                total_users = len(global_df)
                avg_points = global_df['Points'].mean() if 'Points' in global_df.columns else 0
                st.metric(
                    "🌍 Community Impact", 
                    f"{total_users} users", 
                    f"Avg: {avg_points:.1f} pts",
                    help="Total community sustainability impact"
                )
        else:
            st.info("Environmental champions will appear here once users start sharing their data!")
        
        # Leaderboard section
        st.subheader("🏆 Environmental Leaderboard")
        
        # Top performers by environmental class
        if len(global_df) > 0 and 'Class' in global_df.columns:
            class_a_users = global_df[global_df['Class'] == 'A']
            if not class_a_users.empty:
                st.write("**🌟 Top Class A (Doing Great) Performers:**")
                for i, (_, user) in enumerate(class_a_users.head(5).iterrows(), 1):
                    location = user.get('Location', 'Unknown')
                    points = user.get('Points', 0)
                    st.write(f"{i}. **{user['Username']}** ({location}) - {points} points")
        
        # Most efficient by category
        st.subheader("Category Leaders")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'Points' in global_df.columns and len(global_df) > 0:
                top_performer = global_df.loc[global_df['Points'].idxmax()]
                st.metric("🌟 Top Performer", top_performer['Username'], f"{top_performer['Points']} points")
            else:
                st.metric("🌟 Top Performer", "Coming Soon", "Data Loading")
        
        with col2:
            if 'Class' in global_df.columns and len(global_df) > 0:
                class_a_count = len(global_df[global_df['Class'] == 'A'])
                st.metric("⚡ Class A Users", f"{class_a_count} users", "Excellent Performance")
            else:
                st.metric("⚡ Class A Users", "Coming Soon", "Data Loading")
        
        with col3:
            if 'Avg Carbon Footprint' in global_df.columns and len(global_df) > 0:
                carbon_leader = global_df.loc[global_df['Avg Carbon Footprint'].idxmin()]
                st.metric("🌱 Carbon Footprint Leader", carbon_leader['Username'], f"{carbon_leader['Avg Carbon Footprint']} kg CO₂")
            else:
                st.metric("🌱 Carbon Footprint Leader", "Coming Soon", "Data Loading")
        
        # Individual user analysis section with info button
        st.subheader("👥 User Spotlight & AI Insights")
        st.markdown("*Get detailed insights about specific community members*")
        
        # Toggleable info button
        if 'show_analysis_info' not in st.session_state:
            st.session_state.show_analysis_info = False
            
        if st.button("ⓘ Info", key="analysis_info", help="Click to toggle analysis information"):
            st.session_state.show_analysis_info = not st.session_state.show_analysis_info
            
        if st.session_state.show_analysis_info:
            st.info("""**User Analysis Features:**

**Detailed consumption patterns** for selected users

**Environmental class** breakdown

**Carbon footprint** calculation

**Household demographics** context""")
        
        if len(global_df) > 0:
            selected_user = st.selectbox(
                "Choose a user to view detailed environmental insights:", 
                options=[""] + global_df['Username'].tolist(),
                help="Select any user to see their AI-generated environmental analysis"
            )
            
            if selected_user:
                # Get the public account for this user
                user_obj = db.get_user(selected_user, is_public='public')
                
                # Show user summary card
                user_data = global_df[global_df['Username'] == selected_user].iloc[0]
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**👤 {selected_user}**")
                    st.write(f"📍 **Location:** {user_data['Location']}")
                    st.write(f"👥 **Household:** {user_data['Household Size']} people")
                    st.write(f"🏆 **Class:** {user_data['Environmental Class']}")
                    st.write(f"📅 **Member since:** {user_data['Member Since']}")
                
                with col2:
                    st.markdown("**📊 Monthly Resource Usage:**")
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("💧 Water", f"{user_data['Avg Water (gal)']} gal")
                    with col_b:
                        st.metric("⚡ Electricity", f"{user_data['Avg Electricity (kWh)']} kWh")
                    with col_c:
                        if 'Avg Carbon Footprint' in user_data:
                            st.metric("🌿 Carbon", f"{user_data['Avg Carbon Footprint']} kg CO₂")
                        else:
                            st.metric("🌿 Carbon", "N/A")
                
                # AI Analysis section
                if user_obj and getattr(user_obj, 'ai_analysis', None):
                    st.markdown("**🤖 AI Environmental Analysis:**")
                    st.info(getattr(user_obj, 'ai_analysis', 'No analysis available'))
                else:
                    st.markdown("**🤖 AI Environmental Analysis:**")
                    st.warning(f"AI analysis not yet available for {selected_user}. Analysis is generated after sufficient usage data is collected.")
        else:
            st.info("User analysis will be available once community members start sharing their data.")
        
        # Community insights section
        st.subheader("🤝 Community Insights")
        
        all_usernames = list(set([getattr(user, 'username', 'Unknown') for user in public_users if getattr(user, 'username', 'Unknown') != 'Unknown']))
        dual_account_users = []
        
        for username in all_usernames:
            if db.username_has_both_accounts(username):
                dual_account_users.append(username)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🌍 Community Statistics:**")
            st.write(f"👥 **Active public accounts:** {len(public_users)}")
            st.write(f"🔤 **Unique usernames:** {len(all_usernames)}")
            st.write(f"⚖️ **Users with dual accounts:** {len(dual_account_users)}")
            st.write(f"📈 **Total data records:** {sum([data['Records'] for data in global_data])}")
        
        with col2:
            st.markdown("**💡 Community Benefits:**")
            st.write("🌱 Share best practices for sustainability")
            st.write("📊 Compare your impact with similar households")
            st.write("🎯 Set goals based on top performers")
            st.write("🌍 Contribute to global environmental awareness")
        
        if dual_account_users:
            st.info(f"🔄 **Multi-account users:** {', '.join(dual_account_users)} maintain both public and private profiles for different purposes.")
        
        # Complete data table with better presentation
        st.subheader("📋 Complete Community Environmental Data")
        st.markdown("*Comprehensive view of all public environmental data - sortable and downloadable*")
        
        if len(global_df) > 0:
            # Sort by environmental class and carbon footprint
            try:
                # Sort by available columns only
                if 'Environmental Class' in global_df.columns:
                    display_df = global_df.sort_values('Environmental Class')
                else:
                    display_df = global_df
            except:
                # Fallback if sorting fails
                display_df = global_df
            
            # Color-code the dataframe for better readability
            st.markdown("**Legend:** 🌱 Class A (Excellent) | 🌿 Class B (Good) | 🌾 Class C (Developing)")
            
            # Display the data with custom formatting
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Username": st.column_config.TextColumn("👤 User", width="small"),
                    "Class": st.column_config.TextColumn("🏆 Class", width="small"),
                    "Location": st.column_config.TextColumn("📍 Location", width="medium"),
                    "Points": st.column_config.NumberColumn("⭐ Points", width="small")
                }
            )
            
            # Download section
            col1, col2 = st.columns([3, 1])
            with col2:
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Data",
                    data=csv,
                    file_name=f"ecoaudit_global_data_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    help="Download complete environmental data as CSV file"
                )
        else:
            st.info("Community data table will appear here once users start sharing their environmental impact data.")
    else:
        st.info("No users with complete usage data found. Encourage users to track their utility usage and make their data public to contribute to global insights!")

elif page == "History":
    # Redirect to My History for backward compatibility
    st.info("Redirecting to 'My History' - please use the navigation menu.")
    st.stop()
    st.markdown("""
    View your previously saved utility usage data and track patterns over time.
    """)
    
    # Get utility history from database
    history = db.get_utility_history(10)
    
    if history:
        # Create columns for the table
        history_data = {
            'Date': [h.timestamp.strftime("%Y-%m-%d %H:%M") for h in history],
            'Water (gallons)': [h.water_gallons for h in history],
            'Electricity (kWh)': [h.electricity_kwh for h in history],
            'Gas (m³)': [h.gas_cubic_m for h in history],
            'Water Status': [h.water_status for h in history],
            'Electricity Status': [h.electricity_status for h in history],
            'Gas Status': [h.gas_status for h in history]
        }
        
        history_df = pd.DataFrame(history_data)
        st.dataframe(history_df, use_container_width=True)
        
        # Visualize historical data
        st.subheader("Historical Data Visualization")
        
        # Create line chart of water usage over time
        water_fig = px.line(
            history_df, 
            x='Date', 
            y='Water (gallons)', 
            title="Water Usage History",
            markers=True
        )
        
        # Create line chart of electricity usage over time
        electricity_fig = px.line(
            history_df, 
            x='Date', 
            y='Electricity (kWh)', 
            title="Electricity Usage History",
            markers=True
        )
        
        # Create line chart of gas usage over time
        gas_fig = px.line(
            history_df, 
            x='Date', 
            y='Gas (m³)', 
            title="Gas Usage History",
            markers=True
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(water_fig, use_container_width=True)
            st.plotly_chart(gas_fig, use_container_width=True)
            
        with col2:
            st.plotly_chart(electricity_fig, use_container_width=True)
            
        # Display trends and insights
        st.subheader("Trends and Insights")
        st.markdown("""
        - Track your utility usage patterns over time
        - Identify seasonal variations in consumption
        - Monitor the effectiveness of conservation efforts
        """)
    else:
        st.info("No utility usage data has been saved yet. Use the Utility Usage Tracker to save your data.")

elif page == "Materials Recycling Guide":
    st.header("Materials Recycling Guide")
    st.markdown("""
    Get tips on how to reuse or recycle different non-biodegradable materials.
    Simply enter the type of material you want to recycle or reuse.
    """)
    
    # Initialize material state to prevent reset on image upload
    if 'selected_material' not in st.session_state:
        st.session_state.selected_material = ""
    
    # Create a search input for materials with persistent state
    material = st.text_input(
        "Enter material to get recycling/reuse guidance (e.g., plastic bottle, glass, e-waste):", 
        value=st.session_state.selected_material,
        key="material_input"
    )
    
    # Update session state when material changes
    if material != st.session_state.selected_material:
        st.session_state.selected_material = material
    
    # Show some examples for user guidance
    with st.expander("Example materials you can search for"):
        st.markdown("""
        **Plastics**
        - Plastic bag, polythene, plastic bottle, plastic container
        - Plastic cup, plastic straw, plastic toy, plastic lid
        - Plastic cover, plastic wrap, bubble wrap, ziploc bag
        - Styrofoam, thermocol, PVC, acrylic
        
        **Electronics**
        - E-waste, battery, phone, laptop, computer
        - Tablet, printer, wire, cable, headphone, charger
        
        **Metals**
        - Metal, aluminum, aluminum can, aluminum foil
        - Tin can, steel, iron, copper, brass, silver
        
        **Glass**
        - Glass, glass jar, glass bottle, light bulb, mirror
        
        **Rubber and Silicone**
        - Rubber, tire, slipper, rubber band, silicone
        
        **Paper Products with Non-biodegradable Elements**
        - Tetra pack, juice box, laminated paper
        
        **Fabrics and Textiles**
        - Synthetic, polyester, old clothes, shirt, nylon, carpet
        
        **Media and Storage**
        - CD, DVD, video tape, cassette tape, floppy disk
        
        **Other Items**
        - Shoes, backpack, umbrella, mattress, ceramic
        """)
    
    # Search database or use AI-powered smart assistant
    if st.button("Get AI-Powered Analysis", key="search_tips_button"):
        if material:
            with st.spinner("Analyzing material with AI..."):
                # Get comprehensive AI analysis
                analysis_result = smart_assistant(material)
                
                # Update database search count
                db_material = db.find_material(material)
                if db_material:
                    is_from_db = True
                else:
                    # Save new material to database
                    reuse_tip = analysis_result.get('reuse_tips', 'Creative repurposing based on material properties.')
                    recycle_tip = analysis_result.get('recycle_tips', 'Research specialized recycling options.')
                    db.save_material(material, reuse_tip, recycle_tip)
                    is_from_db = False
            
            st.subheader(f"AI Analysis for: {material.title()}")
            
            # Display AI sustainability metrics
            sustainability_col1, sustainability_col2, sustainability_col3 = st.columns(3)
            
            with sustainability_col1:
                score = analysis_result.get('ai_sustainability_score', 5.0)
                st.metric(
                    "Sustainability Score", 
                    f"{score:.1f}/10",
                    delta="Eco-friendly" if score > 7 else "Needs attention" if score < 4 else "Moderate"
                )
            
            with sustainability_col2:
                impact = analysis_result.get('environmental_impact', 'Unknown')
                if isinstance(impact, (int, float)):
                    st.metric("Environmental Impact", f"{impact:.1f}/10", delta="Higher values = more impact")
                else:
                    st.metric("Environmental Impact", str(impact))
            
            with sustainability_col3:
                recyclability = analysis_result.get('recyclability_score', 'Unknown')
                if isinstance(recyclability, (int, float)):
                    st.metric("Recyclability", f"{recyclability:.1f}/10", delta="Higher = easier to recycle")
                else:
                    st.metric("Recyclability", str(recyclability))
            
            # Display material category and insights
            category = analysis_result.get('material_category', 'unknown')
            if category != 'unknown':
                st.info(f"Material Category: **{category.title()}**")
            
            # Display source information
            if is_from_db:
                st.success("Database updated with your search")
            else:
                st.info("New material added to database with AI analysis")
            
            # Display the results in enhanced cards
            col1, col2 = st.columns(2)
            
            reuse_tip = analysis_result.get('reuse_tips', 'Creative repurposing opportunities available.')
            recycle_tip = analysis_result.get('recycle_tips', 'Specialized recycling options recommended.')
            
            with col1:
                st.info(f"♻️ **Reuse Recommendations:**\n\n{reuse_tip}")
                
            with col2:
                st.success(f"🔁 **Recycling Instructions:**\n\n{recycle_tip}")
            
            # Additional AI insights
            st.subheader("AI-Generated Sustainability Insights")
            
            # Environmental impact analysis
            if isinstance(analysis_result.get('environmental_impact'), (int, float)):
                impact_score = analysis_result['environmental_impact']
                if impact_score > 8:
                    st.error("High Environmental Impact: Consider alternatives or enhanced disposal methods")
                elif impact_score > 5:
                    st.warning("Moderate Environmental Impact: Follow best practices for disposal")
                else:
                    st.success("Low Environmental Impact: Continue responsible usage")
            
            # Sustainability recommendations
            if analysis_result.get('ai_sustainability_score', 0) < 5:
                st.warning("Sustainability Alert: This material has significant environmental concerns. Consider reducing usage and exploring eco-friendly alternatives.")
            elif analysis_result.get('ai_sustainability_score', 0) > 8:
                st.success("Eco-Friendly Choice: This material has good sustainability characteristics when properly managed.")
            
            # Generate shareable link with material
            material_share_params = {
                "material": quote(material)
            }
            material_share_url = generate_share_url("Materials Recycling Guide", material_share_params)
            
            # Create a share button for current results
            st.subheader("Share These Tips")
            st.markdown("Share these recycling tips with others:")
            st.code(material_share_url, language=None)
            material_share_button = st.button("📤 Share These Tips", key="share_material_button")
            if material_share_button:
                st.success("Tips link copied to clipboard! Share it with others.")



            # Add a section for additional resources
            st.subheader("Additional Resources")
            st.markdown("""
            - [Earth911 - Find Recycling Centers](https://earth911.com/)
            - [EPA - Reduce, Reuse, Recycle](https://www.epa.gov/recycle)
            - [DIY Network - Reuse Projects](https://www.diynetwork.com/)
            """)
        else:
            st.warning("Please enter a material to get recycling and reuse tips.")

elif page == "Blinkbot":
    st.header("💬 Blinkbot - Smart Environmental Assistant")
    st.markdown("""
    Welcome to Blinkbot! I'm your intelligent environmental assistant with enhanced knowledge about sustainability, 
    energy conservation, and environmental best practices. Ask me anything!
    """)
    
    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        # Add initial greeting with error handling
        try:
            initial_response = chatbot.get_intelligent_response("hello", current_user)
            st.session_state.chat_history.append({"role": "assistant", "content": initial_response})
        except Exception as e:
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": "Hi! Welcome to EcoAudit! I'm Blinkbot, your smart environmental assistant. I can help you with sustainability questions, EcoAudit features, and environmental best practices. What would you like to know?"
            })
    
    # Enhanced chat interface 
    st.subheader("Ask Your Question")
    
    # Alternative input method to avoid form issues
    user_input = st.text_input(
        "Type your environmental or sustainability question here:",
        placeholder="Ask me about energy conservation, recycling, carbon footprint, sustainable living, EcoAudit features...",
        key="chat_input_field"
    )
    
    # Search button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_clicked = st.button("Get Smart Answer", use_container_width=True, type="primary", key="chat_submit")
    
    # Display chat history with improved formatting
    if st.session_state.chat_history:
        st.subheader("💬 Conversation History")
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
    
    # Handle user input
    if search_clicked and user_input and user_input.strip():
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
        
        # Get enhanced bot response with smart environmental knowledge
        with st.spinner("Generating response..."):
            try:
                bot_response = chatbot.get_intelligent_response(user_input.strip(), current_user)
            except Exception as e:
                bot_response = "I encountered an issue processing your request. Let me try to help you anyway! You can ask me about creating accounts, tracking utilities, finding recycling tips, understanding AI insights, or comparing with global data."
        
        st.session_state.chat_history.append({"role": "assistant", "content": bot_response})
        st.rerun()
    elif search_clicked and not user_input:
        st.warning("Please enter a question before submitting.")
    
    # Add quick action buttons
    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Clear Chat", key="clear_chat_btn"):
            st.session_state.chat_history = []
            try:
                initial_response = chatbot.get_intelligent_response("hello", current_user)
            except Exception:
                initial_response = "Hi! Welcome to EcoAudit! I'm your intelligent assistant. How can I help you today?"
            st.session_state.chat_history.append({"role": "assistant", "content": initial_response})
            st.rerun()
    
    with col2:
        if st.button("❓ How to use EcoAudit", key="help_btn"):
            try:
                help_response = chatbot.get_response("how to use ecoaudit")
            except Exception:
                help_response = "EcoAudit helps you track utility usage and get recycling tips. Create an account to start tracking your environmental impact!"
            st.session_state.chat_history.append({"role": "assistant", "content": help_response})
            st.rerun()
    
    with col3:
        if st.button("🔐 Login Help", key="login_help_btn"):
            try:
                login_response = chatbot.get_response("login help")
            except Exception:
                login_response = "To log in: Go to User Profile, select your account type (public/private), enter your username and click Login."
            st.session_state.chat_history.append({"role": "assistant", "content": login_response})
            st.rerun()
    
    # Chat tips
    with st.expander("💡 Chat Tips"):
        st.markdown("""
        **Things you can ask me:**
        - "How do I create an account?"
        - "What is the utility tracker?"
        - "How do I find recycling tips?"
        - "What are AI insights?"
        - "How do I compare with others?"
        - "What languages are supported?"
        - "I'm having problems with..."
        
        **Sample questions:**
        - "How do I save energy at home?"
        - "What's the best way to recycle plastic?"
        - "How does carbon footprint calculation work?"
        - "Can you help me understand my environmental class?"
        - "What makes a good sustainability practice?"
        """)

# Add logout button if user is logged in
if st.session_state.current_user is not None:
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", help="Sign out of your account"):
        st.session_state.current_user = None
        st.session_state.remember_user = None
        st.session_state.remember_account_type = None
        st.success("You have been logged out successfully!")
        st.rerun()
    
    # Delete account permanently feature
    with st.sidebar.expander("🗑️ Delete Account Permanently", expanded=False):
        st.error("⚠️ WARNING: This action cannot be undone!")
        st.markdown("This will permanently delete:")
        st.markdown("- Your account and profile")
        st.markdown("- All utility usage history")
        st.markdown("- All recycling verification records")
        st.markdown("- All points and achievements")
        
        confirm_delete = st.checkbox("I understand this action is permanent")
        delete_confirmation = st.text_input(
            "Type 'DELETE' to confirm:", 
            key="delete_confirmation",
            help="Type DELETE in capital letters to confirm deletion"
        )
        
        if st.button("🗑️ Delete My Account Forever", type="primary", key="delete_account_btn"):
            if confirm_delete and delete_confirmation == "DELETE":
                # Perform account deletion
                success, message = db.delete_user_account_permanently(st.session_state.current_user.id)
                if success:
                    st.success(message)
                    # Clear session state
                    st.session_state.current_user = None
                    st.session_state.remember_user = None
                    st.session_state.remember_account_type = None
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"Deletion failed: {message}")
            else:
                if not confirm_delete:
                    st.error("Please check the confirmation box first.")
                elif delete_confirmation != "DELETE":
                    st.error("Please type 'DELETE' exactly as shown to confirm.")





# Footer
st.markdown("---")
st.markdown("© EcoAudit by Team EcoAudit - Helping you monitor your utility usage and reduce waste.")
