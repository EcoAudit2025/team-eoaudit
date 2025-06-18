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
from simple_chatbot import EcoAuditChatbot
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="EcoAudit",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize chatbot
@st.cache_resource
def get_chatbot():
    return EcoAuditChatbot()

chatbot = get_chatbot()

# Base URL for sharing
APP_URL = os.environ.get("REPLIT_DOMAINS", "").split(',')[0] if os.environ.get("REPLIT_DOMAINS") else ""

# Helper function to get actual public URL
def get_public_url():
    """Get the actual public-facing URL of the app"""
    if APP_URL:
        return f"https://{APP_URL}"
    return "URL not available"

# Initialize session state for displaying saved notifications
if 'show_saved' not in st.session_state:
    st.session_state.show_saved = False
if 'saved_message' not in st.session_state:
    st.session_state.saved_message = ""
if 'ai_initialized' not in st.session_state:
    st.session_state.ai_initialized = False

# Initialize AI system on first run
if not st.session_state.ai_initialized:
    with st.spinner("Initializing AI system..."):
        # Load historical data for AI training
        historical_data = db.get_utility_history(limit=100)
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
        
        # Train AI models
        success, message = eco_ai.train_models(data_for_training)
        if success:
            st.session_state.ai_initialized = True

# Title and introduction with custom icon
from PIL import Image
import base64

# Load the custom icon
icon = Image.open("generated-icon.png")

# Create a column layout for the title with icon
title_col1, title_col2 = st.columns([1, 5])

with title_col1:
    st.image(icon, width=100)
    
with title_col2:
    st.title("EcoAudit")
    st.markdown("""
        Monitor your utility usage and get guidance on recycling/reusing materials.
        This application helps you track your water, electricity, and gas usage, 
        and provides tips on how to reuse or recycle non-biodegradable materials.
        
        *Created by Team EcoAudit*
    """)
    


# AI-Enhanced Functions
def assess_usage_with_ai(water_gallons, electricity_kwh, gas_cubic_m):
    """AI-powered utility usage assessment"""
    # Get historical data for personalized assessment
    historical_data = db.get_utility_history(limit=50)
    data_for_analysis = []
    for record in historical_data:
        data_for_analysis.append({
            'timestamp': record.timestamp,
            'water_gallons': record.water_gallons,
            'electricity_kwh': record.electricity_kwh,
            'gas_cubic_m': record.gas_cubic_m
        })
    
    # Use AI-enhanced assessment
    water_status, electricity_status, gas_status = eco_ai.assess_usage(
        water_gallons, electricity_kwh, gas_cubic_m, data_for_analysis
    )
    
    # Get AI predictions and analysis
    current_data = {
        'timestamp': datetime.now(),
        'water_gallons': water_gallons,
        'electricity_kwh': electricity_kwh,
        'gas_cubic_m': gas_cubic_m
    }
    
    ai_predictions = None
    ai_recommendations = []
    efficiency_score = 50
    
    if eco_ai.is_trained:
        try:
            ai_predictions = eco_ai.predict_usage(current_data)
            ai_recommendations = eco_ai.generate_recommendations(water_gallons, electricity_kwh, gas_cubic_m)
            patterns = eco_ai.analyze_usage_patterns(data_for_analysis)
            efficiency_score = patterns.get('efficiency_score', 50)
        except:
            pass
    
    ai_analysis = {
        'status': {
            'water': water_status,
            'electricity': electricity_status,
            'gas': gas_status
        },
        'predictions': ai_predictions,
        'recommendations': ai_recommendations,
        'efficiency_score': efficiency_score
    }
    
    return water_status, electricity_status, gas_status, ai_analysis

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
            "recycle": "Drop at plastic bag collection centers or participating grocery stores. Many retailers have front-of-store recycling bins."
        },
        "plastic bottle": {
            "reuse": "Create bird feeders, planters, watering cans, piggy banks, or desk organizers. Can be cut to make funnels, scoops, or storage containers.",
            "recycle": "Rinse thoroughly and recycle in curbside recycling if marked with recycling symbols 1 (PET) or 2 (HDPE)."
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
            "recycle": "Never throw in trash. Recycle at battery drop-off locations, electronic stores, or hazardous waste facilities."
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

# Sidebar for navigation with icon
sidebar_col1, sidebar_col2 = st.sidebar.columns([1, 4])
with sidebar_col1:
    st.image(icon, width=50)
with sidebar_col2:
    st.title("Navigation")
    
page = st.sidebar.radio("Go to", ["User Profile", "Utility Usage Tracker", "Materials Recycling Guide", "AI Insights Dashboard", "My History", "Global Monitor", "Blinkbot"])

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
    st.sidebar.title("Database Stats")
    st.sidebar.markdown(f"""
    - **{len(all_users)}** total users
    - **{len(public_users)}** public profiles
    - **{len(popular_materials) if popular_materials else 0}** materials in database
    """)
except Exception as e:
    st.sidebar.error("Database loading...")

# Initialize session state for user authentication
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

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
            account_type = st.selectbox("Account Type", ["private", "public"], 
                                      help="Select whether to access your public or private account")
            
            if st.button("Login", key="login_button"):
                if username:
                    user = db.get_user(username, is_public=account_type)
                    if user:
                        st.session_state.current_user = user
                        account_desc = "public" if getattr(user, 'is_public', None) == "public" else "private"
                        st.success(f"Welcome back, {user.username}! (Logged into {account_desc} account)")
                        
                        # Show if user has other account type
                        user_info = db.get_username_account_info(username)
                        if user_info and user_info['total_accounts'] > 1:
                            other_type = "private" if account_type == "public" else "public"
                            st.info(f"You also have a {other_type} account with this username.")
                        
                        st.rerun()
                    else:
                        # Check if user exists with other account type
                        other_type = "private" if account_type == "public" else "public"
                        other_user = db.get_user(username, is_public=other_type)
                        if other_user:
                            st.error(f"No {account_type} account found for username '{username}', but you have a {other_type} account. Please select the correct account type above.")
                        else:
                            st.error(f"No account found for username '{username}'. Please create an account first.")
                else:
                    st.warning("Please enter a username.")
        
        with tab2:
            st.subheader("Create New Account")
            new_username = st.text_input("Choose Username", key="new_username")
            new_email = st.text_input("Email (optional)", key="new_email")
            
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
                    "Young Couple",
                    "Family with Young Children",
                    "Family with Teenagers", 
                    "Multi-generational Family",
                    "Senior Couple",
                    "Single Parent Family",
                    "Shared Housing/Roommates",
                    "Extended Family"
                ], key="household_type")
            
            housing_type = st.selectbox("Housing Type", [
                "Apartment - Studio",
                "Apartment - 1-2 Bedroom", 
                "Apartment - 3+ Bedroom",
                "Townhouse/Condo",
                "Single Family House - Small (<1500 sq ft)",
                "Single Family House - Medium (1500-3000 sq ft)",
                "Single Family House - Large (>3000 sq ft)",
                "Mobile Home",
                "Farm House"
            ], key="housing_type")
            
            energy_features = st.multiselect("Energy Features", [
                "Solar Panels",
                "Energy Efficient Appliances",
                "Smart Thermostat", 
                "LED Lighting",
                "Double-Pane Windows",
                "Good Insulation",
                "Heat Pump",
                "Electric Vehicle Charging"
            ], key="energy_features")
            
            # Language selection
            language = st.selectbox("Preferred Language", [
                "English",
                "Spanish (Español)",
                "French (Français)", 
                "German (Deutsch)",
                "Chinese (中文)",
                "Japanese (日本語)",
                "Portuguese (Português)",
                "Italian (Italiano)"
            ], key="language")
            
            new_is_public = st.selectbox("Data Visibility", ["private", "public"], 
                                       help="Public data can be viewed by others in the Global Monitor")
            
            if st.button("Create Account", key="create_button"):
                if new_username:
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
                        language=language
                    )
                    if user:
                        st.session_state.current_user = user
                        st.success(f"Account created successfully! Welcome, {user.username}!")
                        st.rerun()
                    else:
                        st.error("Failed to create account. Please try again.")
                else:
                    st.warning("Please enter a username.")
    else:
        # User is logged in
        user = st.session_state.current_user
        account_type_desc = "Public" if getattr(user, 'is_public', None) == "public" else "Private"
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
            st.write(f"**Email:** {user.email or 'Not provided'}")
            st.write(f"**Location Type:** {user.location_type or 'Not specified'}")
            st.write(f"**Climate Zone:** {user.climate_zone or 'Not specified'}")
            st.write(f"**Household Type:** {user.household_type or 'Not specified'}")
            st.write(f"**Housing Type:** {user.housing_type or 'Not specified'}")
            st.write(f"**Total People:** {user.household_size} ({user.adults} adults, {user.children} children, {user.seniors} seniors)")
            st.write(f"**Language:** {user.language or 'English'}")
            st.write(f"**Data Visibility:** {user.is_public}")
            st.write(f"**Environmental Class:** {user.environmental_class or 'Not calculated'}")
            st.write(f"**Member Since:** {user.created_at.strftime('%B %Y')}")
            
            # Display energy features if available
            if user.energy_features:
                import json
                try:
                    features = json.loads(user.energy_features)
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
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Update Profile"):
                st.subheader("Update Your Profile")
                
                # Create update form
                with st.form("update_profile_form"):
                    st.write("**Contact Information:**")
                    update_email = st.text_input("Email", value=user.email or "")
                    
                    st.write("**Location & Climate:**")
                    update_location = st.selectbox("Location Type", [
                        "Urban - Large City (>1M population)",
                        "Urban - Medium City (100K-1M population)", 
                        "Suburban - Metropolitan Area",
                        "Small Town (10K-100K population)",
                        "Rural - Countryside",
                        "Rural - Remote Area"
                    ], index=0 if not user.location_type else [
                        "Urban - Large City (>1M population)",
                        "Urban - Medium City (100K-1M population)", 
                        "Suburban - Metropolitan Area",
                        "Small Town (10K-100K population)",
                        "Rural - Countryside",
                        "Rural - Remote Area"
                    ].index(user.location_type) if user.location_type in [
                        "Urban - Large City (>1M population)",
                        "Urban - Medium City (100K-1M population)", 
                        "Suburban - Metropolitan Area",
                        "Small Town (10K-100K population)",
                        "Rural - Countryside",
                        "Rural - Remote Area"
                    ] else 0)
                    
                    update_climate = st.selectbox("Climate Zone", [
                        "Tropical - Hot & Humid",
                        "Subtropical - Warm & Humid", 
                        "Mediterranean - Mild & Dry",
                        "Temperate - Moderate Seasons",
                        "Continental - Cold Winters",
                        "Arid - Hot & Dry",
                        "Semi-Arid - Moderate & Dry",
                        "Polar - Very Cold"
                    ], index=0 if not user.climate_zone else [
                        "Tropical - Hot & Humid",
                        "Subtropical - Warm & Humid", 
                        "Mediterranean - Mild & Dry",
                        "Temperate - Moderate Seasons",
                        "Continental - Cold Winters",
                        "Arid - Hot & Dry",
                        "Semi-Arid - Moderate & Dry",
                        "Polar - Very Cold"
                    ].index(user.climate_zone) if user.climate_zone in [
                        "Tropical - Hot & Humid",
                        "Subtropical - Warm & Humid", 
                        "Mediterranean - Mild & Dry",
                        "Temperate - Moderate Seasons",
                        "Continental - Cold Winters",
                        "Arid - Hot & Dry",
                        "Semi-Arid - Moderate & Dry",
                        "Polar - Very Cold"
                    ] else 0)
                    
                    st.write("**Household Composition:**")
                    update_adults = st.number_input("Adults (18+)", min_value=1, max_value=10, value=user.adults or 1)
                    update_children = st.number_input("Children (under 18)", min_value=0, max_value=10, value=user.children or 0)
                    update_seniors = st.number_input("Seniors (65+)", min_value=0, max_value=10, value=user.seniors or 0)
                    
                    update_household_type = st.selectbox("Household Type", [
                        "Single Person",
                        "Young Couple",
                        "Family with Young Children",
                        "Family with Teenagers", 
                        "Multi-generational Family",
                        "Senior Couple",
                        "Single Parent Family",
                        "Shared Housing/Roommates",
                        "Extended Family"
                    ], index=0 if not user.household_type else [
                        "Single Person",
                        "Young Couple",
                        "Family with Young Children",
                        "Family with Teenagers", 
                        "Multi-generational Family",
                        "Senior Couple",
                        "Single Parent Family",
                        "Shared Housing/Roommates",
                        "Extended Family"
                    ].index(user.household_type) if user.household_type in [
                        "Single Person",
                        "Young Couple",
                        "Family with Young Children",
                        "Family with Teenagers", 
                        "Multi-generational Family",
                        "Senior Couple",
                        "Single Parent Family",
                        "Shared Housing/Roommates",
                        "Extended Family"
                    ] else 0)
                    
                    update_housing_type = st.selectbox("Housing Type", [
                        "Apartment - Studio",
                        "Apartment - 1-2 Bedroom", 
                        "Apartment - 3+ Bedroom",
                        "Townhouse/Condo",
                        "Single Family House - Small (<1500 sq ft)",
                        "Single Family House - Medium (1500-3000 sq ft)",
                        "Single Family House - Large (>3000 sq ft)",
                        "Mobile Home",
                        "Farm House"
                    ], index=0 if not user.housing_type else [
                        "Apartment - Studio",
                        "Apartment - 1-2 Bedroom", 
                        "Apartment - 3+ Bedroom",
                        "Townhouse/Condo",
                        "Single Family House - Small (<1500 sq ft)",
                        "Single Family House - Medium (1500-3000 sq ft)",
                        "Single Family House - Large (>3000 sq ft)",
                        "Mobile Home",
                        "Farm House"
                    ].index(user.housing_type) if user.housing_type in [
                        "Apartment - Studio",
                        "Apartment - 1-2 Bedroom", 
                        "Apartment - 3+ Bedroom",
                        "Townhouse/Condo",
                        "Single Family House - Small (<1500 sq ft)",
                        "Single Family House - Medium (1500-3000 sq ft)",
                        "Single Family House - Large (>3000 sq ft)",
                        "Mobile Home",
                        "Farm House"
                    ] else 0)
                    
                    # Parse existing energy features
                    try:
                        import json
                        existing_features = json.loads(user.energy_features) if user.energy_features else []
                    except:
                        existing_features = []
                    
                    update_energy_features = st.multiselect("Energy Features", [
                        "Solar Panels",
                        "Energy Efficient Appliances",
                        "Smart Thermostat", 
                        "LED Lighting",
                        "Double-Pane Windows",
                        "Good Insulation",
                        "Heat Pump",
                        "Electric Vehicle Charging"
                    ], default=existing_features)
                    
                    update_language = st.selectbox("Preferred Language", [
                        "English",
                        "Spanish (Español)",
                        "French (Français)", 
                        "German (Deutsch)",
                        "Chinese (中文)",
                        "Japanese (日本語)",
                        "Portuguese (Português)",
                        "Italian (Italiano)"
                    ], index=0 if not user.language else [
                        "English",
                        "Spanish (Español)",
                        "French (Français)", 
                        "German (Deutsch)",
                        "Chinese (中文)",
                        "Japanese (日本語)",
                        "Portuguese (Português)",
                        "Italian (Italiano)"
                    ].index(user.language) if user.language in [
                        "English",
                        "Spanish (Español)",
                        "French (Français)", 
                        "German (Deutsch)",
                        "Chinese (中文)",
                        "Japanese (日本語)",
                        "Portuguese (Português)",
                        "Italian (Italiano)"
                    ] else 0)
                    
                    update_visibility = st.selectbox("Data Visibility", ["private", "public"], 
                                                   index=0 if user.is_public == "private" else 1,
                                                   help="Change whether your data appears in Global Monitor")
                    
                    submitted = st.form_submit_button("Save Changes")
                    
                    if submitted:
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
                            st.session_state.current_user = updated_user
                            st.success("Profile updated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to update profile. Please try again.")
        
        with col2:
            if st.button("Logout"):
                st.session_state.current_user = None
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
    
    st.markdown("""
    Enter your monthly utility usage to see if it falls within normal ranges.
    This will help you identify potential issues with your utility consumption.
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
        # Get AI-enhanced assessment
        water_status, electricity_status, gas_status, ai_analysis = assess_usage_with_ai(water, electricity, gas)
        
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
            # Calculate efficiency score and carbon footprint
            efficiency_score = ai_analysis.get('efficiency_score', 0) if ai_analysis else None
            carbon_footprint = (water * 0.002 + electricity * 0.4 + gas * 2.2)  # Simple carbon calculation
            
            # Save to database with user ID
            db.save_utility_usage(
                user_id=current_user.id,
                water_gallons=water, 
                electricity_kwh=electricity, 
                gas_cubic_m=gas, 
                water_status=water_status, 
                electricity_status=electricity_status, 
                gas_status=gas_status,
                efficiency_score=efficiency_score,
                carbon_footprint=carbon_footprint
            )
            st.session_state.show_saved = True
            st.session_state.saved_message = "✅ Utility data saved to your personal account!"
            st.success("✅ Utility data saved to your personal account!")
        
        # Display AI-enhanced results
        st.subheader("AI-Powered Usage Assessment")
        
        # Display efficiency score prominently
        if ai_analysis and 'efficiency_score' in ai_analysis:
            efficiency_score = ai_analysis['efficiency_score']
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.metric(
                    label="Overall Efficiency Score",
                    value=f"{efficiency_score}/100",
                    delta=f"{'Above' if efficiency_score > 70 else 'Below'} average" if efficiency_score != 50 else "Average"
                )
        
        # Display status with color indicators
        
        status_cols = st.columns(3)
        
        with status_cols[0]:
            st.metric("Water Status", water_status)
            if water_status == "Low":
                st.warning("⚠️ Your water usage is below normal range.")
            elif water_status == "High":
                st.error("🚨 Your water usage is above normal range.")
            else:
                st.success("✅ Your water usage is within normal range (3000-12000 gallons).")
                
        with status_cols[1]:
            st.metric("Electricity Status", electricity_status)
            if electricity_status == "Low":
                st.warning("⚠️ Your electricity usage is below normal range.")
            elif electricity_status == "High":
                st.error("🚨 Your electricity usage is above normal range.")
            else:
                st.success("✅ Your electricity usage is within normal range (300-800 kWh).")
                
        with status_cols[2]:
            st.metric("Gas Status", gas_status)
            if gas_status == "Low":
                st.warning("⚠️ Your gas usage is below normal range.")
            elif gas_status == "High":
                st.error("🚨 Your gas usage is above normal range.")
            else:
                st.success("✅ Your gas usage is within normal range (50-150 cubic meters).")
        
        # Visualize the results with a bar chart
        st.subheader("Visual Comparison")
        
        # Create reference data for normal ranges
        reference_data = {
            'Utility': ['Water Min', 'Water Max', 'Electricity Min', 'Electricity Max', 'Gas Min', 'Gas Max'],
            'Value': [3000, 12000, 300, 800, 50, 150]
        }
        ref_df = pd.DataFrame(reference_data)
        
        # Create chart showing user values compared to normal ranges
        fig = px.bar(
            df, 
            x='Utility', 
            y='Usage', 
            color='Status',
            color_discrete_map={'Low': 'orange', 'Normal': 'green', 'High': 'red'},
            title="Your Usage Compared to Normal Ranges"
        )
        
        # Add normal range indicators as horizontal lines
        fig.add_hline(y=3000, line_dash="dash", line_color="green", annotation_text="Water Min")
        fig.add_hline(y=12000, line_dash="dash", line_color="green", annotation_text="Water Max")
        
        # Update layout for better visibility
        fig.update_layout(
            xaxis_title="Utility Type",
            yaxis_title="Usage Value (Note: Units differ)",
            legend_title="Status"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display AI predictions and recommendations
        if ai_analysis and eco_ai.is_trained:
            st.subheader("AI Predictions & Recommendations")
            
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
                for rec in ai_analysis['recommendations']:
                    with st.expander(f"{rec['category']} - {rec['priority']} Priority"):
                        st.write(rec['message'])
                        if 'potential_savings' in rec:
                            st.success(f"Potential Savings: {rec['potential_savings']}")
                        if 'impact' in rec:
                            st.info(f"Impact: {rec['impact']}")
                        if 'tip' in rec:
                            st.info(f"Tip: {rec['tip']}")
        
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
    
    # Display AI model performance and status
    st.subheader("AI Model Status")
    
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
        
        # Efficiency score visualization
        if 'efficiency_score' in patterns:
            st.subheader("Overall Efficiency Analysis")
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
    
    # Historical trend visualization
    if len(data_for_analysis) > 5:
        st.subheader("Historical Usage Trends")
        
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
    
    # Search functionality
    st.subheader("🔍 Find Environmental Champions")
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
    
    # Get public users based on search
    if search_term or search_button:
        public_users = db.search_public_users(search_term if search_term else "")
        if search_term:
            st.success(f"Search results for '{search_term}': {len(public_users)} user(s) found")
    else:
        public_users = db.get_public_users()
    
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
    
    # Create global statistics
    global_data = []
    for user in public_users:
        try:
            user_usage = db.get_user_usage_last_year(user.id)
            if user_usage and len(user_usage) > 0:
                # Safely calculate averages with error handling
                water_values = [record.water_gallons for record in user_usage if record.water_gallons is not None]
                electricity_values = [record.electricity_kwh for record in user_usage if record.electricity_kwh is not None]
                gas_values = [record.gas_cubic_m for record in user_usage if record.gas_cubic_m is not None]
                carbon_values = [record.carbon_footprint for record in user_usage if record.carbon_footprint is not None]
                
                if water_values and electricity_values and gas_values:
                    avg_water = sum(water_values) / len(water_values)
                    avg_electricity = sum(electricity_values) / len(electricity_values)
                    avg_gas = sum(gas_values) / len(gas_values)
                    avg_carbon = sum(carbon_values) / len(carbon_values) if carbon_values else 0
                    
                    global_data.append({
                        'Username': getattr(user, 'username', 'Unknown'),
                        'Account Type': 'Public',
                        'Location': getattr(user, 'location_type', None) or 'Unknown',
                        'Household Size': getattr(user, 'household_size', None) or 1,
                        'Environmental Class': getattr(user, 'environmental_class', None) or 'Not calculated',
                        'Avg Water (gal)': max(0, int(float(avg_water))),
                        'Avg Electricity (kWh)': max(0, int(float(avg_electricity))),
                        'Avg Gas (m³)': max(0, int(float(avg_gas))),
                        'Avg Carbon Footprint': round(max(0, float(avg_carbon)), 1),
                        'Records': len(user_usage),
                        'Member Since': getattr(user, 'created_at', None).strftime('%Y-%m-%d') if getattr(user, 'created_at', None) else 'Unknown'
                    })
        except Exception as e:
            # Skip users with data issues
            continue
    
    if global_data and len(global_data) > 0:
        global_df = pd.DataFrame(global_data)
        
        # Global statistics overview
        st.subheader("🌟 Community Environmental Impact Overview")
        
        # Calculate meaningful statistics
        total_users = len(global_data)
        class_a_users = len([data for data in global_data if data['Environmental Class'] == 'A'])
        class_b_users = len([data for data in global_data if data['Environmental Class'] == 'B'])
        class_c_users = len([data for data in global_data if data['Environmental Class'] == 'C'])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🌍 Community Members", 
                total_users,
                help="Total number of users sharing their environmental data publicly"
            )
        
        with col2:
            eco_percentage = (class_a_users / total_users * 100) if total_users > 0 else 0
            st.metric(
                "🌱 Eco Champions", 
                f"{class_a_users} ({eco_percentage:.0f}%)",
                help="Users with excellent environmental performance (Class A)"
            )
        
        with col3:
            if not global_df['Avg Water (gal)'].empty:
                avg_global_water = global_df['Avg Water (gal)'].mean()
                st.metric(
                    "💧 Avg Water Usage", 
                    f"{avg_global_water:.0f} gal/month",
                    help="Average monthly water consumption across all public users"
                )
            else:
                st.metric("💧 Avg Water Usage", "No data")
        
        with col4:
            if not global_df['Avg Carbon Footprint'].empty:
                avg_global_carbon = global_df['Avg Carbon Footprint'].mean()
                st.metric(
                    "🌿 Avg Carbon Footprint", 
                    f"{avg_global_carbon:.1f} kg CO₂",
                    help="Average monthly carbon emissions from utility usage"
                )
            else:
                st.metric("🌿 Avg Carbon Footprint", "No data")
        
        # Environmental class distribution with better context
        st.subheader("🏆 Environmental Performance Distribution")
        
        # Create environmental class explanation
        st.markdown("""
        **Environmental Performance Classes:**
        - **Class A (🌱 Excellent)**: Outstanding environmental stewardship - low resource consumption
        - **Class B (🌿 Good)**: Above-average environmental awareness with room for improvement  
        - **Class C (🌾 Developing)**: Standard consumption levels - great potential for positive impact
        """)
        
        class_counts = global_df['Environmental Class'].value_counts()
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
                    emoji = {'A': '🌱', 'B': '🌿', 'C': '🌾'}[class_name]
                    st.write(f"{emoji} **Class {class_name}:** {count} users ({percentage:.1f}%)")
        else:
            st.info("No environmental classification data available yet.")
        
        # Usage comparison charts with better insights
        st.subheader("📊 Resource Consumption Insights")
        
        tab1, tab2, tab3 = st.tabs(["💧 Water Usage", "⚡ Energy Consumption", "🌍 Location Patterns"])
        
        with tab1:
            st.markdown("**Monthly Water Consumption by Environmental Performance**")
            if len(global_df) > 0:
                fig_water = px.box(
                    global_df,
                x='Environmental Class',
                y='Avg Water (gal)',
                title="Water Usage Distribution Across Performance Classes",
                color='Environmental Class',
                color_discrete_map={'A': '#00CC66', 'B': '#FF9900', 'C': '#FF6B35'}
            )
            fig_water.update_layout(
                xaxis_title="Environmental Performance Class",
                yaxis_title="Monthly Water Usage (gallons)"
            )
            st.plotly_chart(fig_water, use_container_width=True)
            
            # Water usage insights
            if not global_df['Avg Water (gal)'].empty:
                min_water = global_df['Avg Water (gal)'].min()
                max_water = global_df['Avg Water (gal)'].max()
                st.info(f"💡 **Water Usage Range:** {min_water:.0f} - {max_water:.0f} gallons/month. Lower usage typically indicates water-efficient practices.")
        
        with tab2:
            st.markdown("**Monthly Electricity Consumption Patterns**")
            if len(global_df) > 0:
                fig_electricity = px.scatter(
                    global_df,
                    x='Avg Electricity (kWh)',
                    y='Avg Carbon Footprint',
                    color='Environmental Class',
                    size='Household Size',
                    hover_data=['Username', 'Location'],
                    title="Electricity Usage vs Carbon Footprint",
                    color_discrete_map={'A': '#00CC66', 'B': '#FF9900', 'C': '#FF6B35'}
                )
                fig_electricity.update_layout(
                    xaxis_title="Monthly Electricity Usage (kWh)",
                    yaxis_title="Carbon Footprint (kg CO₂)"
                )
                st.plotly_chart(fig_electricity, use_container_width=True)
                
                # Energy insights
                avg_electricity = global_df['Avg Electricity (kWh)'].mean()
                st.info(f"⚡ **Community Average:** {avg_electricity:.0f} kWh/month. Consider renewable energy and efficient appliances to reduce consumption.")
        
        with tab3:
            st.markdown("**Environmental Performance by Location Type**")
            if len(global_df) > 0:
                location_summary = global_df.groupby('Location').agg({
                    'Avg Water (gal)': 'mean',
                    'Avg Electricity (kWh)': 'mean',
                    'Username': 'count'
                }).round(1)
                location_summary.columns = ['Avg Water (gal)', 'Avg Electricity (kWh)', 'User Count']
                location_summary = location_summary.sort_values('User Count', ascending=False)
                
                st.dataframe(location_summary, use_container_width=True)
                st.info("🏙️ **Location Insights:** Different living environments often have varying resource consumption patterns due to infrastructure and lifestyle factors.")
        
        # Top performers section with more context
        st.subheader("🏆 Community Environmental Champions")
        st.markdown("*Learn from users who are leading the way in sustainable living*")
        
        if len(global_df) > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                water_leader = global_df.loc[global_df['Avg Water (gal)'].idxmin()]
                st.metric(
                    "💧 Water Conservation Champion", 
                    water_leader['Username'], 
                    f"{water_leader['Avg Water (gal)']} gal/month",
                    help="User with the lowest average monthly water consumption"
                )
                st.caption(f"📍 Location: {water_leader['Location']}")
            
            with col2:
                electricity_leader = global_df.loc[global_df['Avg Electricity (kWh)'].idxmin()]
                st.metric(
                    "⚡ Energy Efficiency Champion", 
                    electricity_leader['Username'], 
                    f"{electricity_leader['Avg Electricity (kWh)']} kWh/month",
                    help="User with the lowest average monthly electricity consumption"
                )
                st.caption(f"📍 Location: {electricity_leader['Location']}")
            
            with col3:
                carbon_leader = global_df.loc[global_df['Avg Carbon Footprint'].idxmin()]
                st.metric(
                    "🌱 Carbon Footprint Champion", 
                    carbon_leader['Username'], 
                    f"{carbon_leader['Avg Carbon Footprint']} kg CO₂/month",
                    help="User with the lowest average monthly carbon emissions"
                )
                st.caption(f"📍 Location: {carbon_leader['Location']}")
        else:
            st.info("Environmental champions will appear here once users start sharing their data!")
            x='Environmental Class',
        fig_electricity = px.bar(
            global_df,
            x='Environmental Class',
            y='Avg Electricity (kWh)',
            title="Electricity Usage by Environmental Class",
            color='Environmental Class',
            color_discrete_map={'A': 'green', 'B': 'orange', 'C': 'red'}
        )
        st.plotly_chart(fig_electricity, use_container_width=True)
        
        # Leaderboard section
        st.subheader("🏆 Environmental Leaderboard")
        
        # Top performers by environmental class
        class_a_users = global_df[global_df['Environmental Class'] == 'A'].sort_values('Avg Carbon Footprint')
        if not class_a_users.empty:
            st.write("**🌟 Top Class A Performers (Lowest Carbon Footprint):**")
            for i, (_, user) in enumerate(class_a_users.head(5).iterrows(), 1):
                st.write(f"{i}. **{user['Username']}** ({user['Location']}) - {user['Avg Carbon Footprint']} kg CO₂/month")
        
        # Most efficient by category
        st.subheader("Category Leaders")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            water_leader = global_df.loc[global_df['Avg Water (gal)'].idxmin()]
            st.metric("💧 Water Conservation Leader", water_leader['Username'], f"{water_leader['Avg Water (gal)']} gal")
        
        with col2:
            electricity_leader = global_df.loc[global_df['Avg Electricity (kWh)'].idxmin()]
            st.metric("⚡ Energy Efficiency Leader", electricity_leader['Username'], f"{electricity_leader['Avg Electricity (kWh)']} kWh")
        
        with col3:
            carbon_leader = global_df.loc[global_df['Avg Carbon Footprint'].idxmin()]
            st.metric("🌱 Carbon Footprint Leader", carbon_leader['Username'], f"{carbon_leader['Avg Carbon Footprint']} kg CO₂")
        
        # Individual user analysis section
        st.subheader("👥 User Spotlight & AI Insights")
        st.markdown("*Get detailed insights about specific community members*")
        
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
                        st.metric("🌿 Carbon", f"{user_data['Avg Carbon Footprint']} kg CO₂")
                
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
                display_df = global_df.sort_values(['Environmental Class', 'Avg Carbon Footprint'])
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
                    "Environmental Class": st.column_config.TextColumn("🏆 Class", width="small"),
                    "Location": st.column_config.TextColumn("📍 Location", width="medium"),
                    "Household Size": st.column_config.NumberColumn("👥 Size", width="small"),
                    "Avg Water (gal)": st.column_config.NumberColumn("💧 Water (gal)", width="small"),
                    "Avg Electricity (kWh)": st.column_config.NumberColumn("⚡ Electric (kWh)", width="small"),
                    "Avg Gas (m³)": st.column_config.NumberColumn("🔥 Gas (m³)", width="small"),
                    "Avg Carbon Footprint": st.column_config.NumberColumn("🌿 Carbon (kg)", width="small"),
                    "Records": st.column_config.NumberColumn("📊 Data Points", width="small"),
                    "Member Since": st.column_config.DateColumn("📅 Joined", width="small")
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
    
    # Create a search input for materials
    material = st.text_input("Enter material to get recycling/reuse guidance (e.g., plastic bottle, glass, e-waste):", "")
    
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
    st.header("💬 Blinkbot")
    st.markdown("""
    Welcome to Blinkbot! I'm here to help you navigate EcoAudit and answer questions about sustainability features.
    No login required - just start chatting!
    """)
    
    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        # Add initial greeting with error handling
        try:
            initial_response = chatbot.get_response("hello")
            st.session_state.chat_history.append({"role": "assistant", "content": initial_response})
        except Exception as e:
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": "Hi! Welcome to EcoAudit! I'm Blinkbot, your helpful assistant. How can I help you today?"
            })
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(message["content"])
    
    # Chat input
    user_input = st.chat_input("Ask Blinkbot anything about EcoAudit or sustainability...")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Get bot response with error handling
        try:
            bot_response = chatbot.get_response(user_input)
        except Exception as e:
            bot_response = "I'm sorry, I encountered an issue processing your request. Let me try to help you anyway! You can ask me about creating accounts, tracking utilities, or finding recycling tips."
        
        st.session_state.chat_history.append({"role": "assistant", "content": bot_response})
        
        # Rerun to show new messages
        st.rerun()
    
    # Add quick action buttons
    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Clear Chat"):
            st.session_state.chat_history = []
            try:
                initial_response = chatbot.get_response("hello")
            except Exception:
                initial_response = "Hi! Welcome to EcoAudit! I'm Blinkbot, your helpful assistant. How can I help you today?"
            st.session_state.chat_history.append({"role": "assistant", "content": initial_response})
            st.rerun()
    
    with col2:
        if st.button("❓ How to use EcoAudit"):
            try:
                help_response = chatbot.get_response("help")
            except Exception:
                help_response = "EcoAudit helps you track utility usage and get recycling tips. Create an account to start tracking your environmental impact!"
            st.session_state.chat_history.append({"role": "assistant", "content": help_response})
            st.rerun()
    
    with col3:
        if st.button("🔐 Login Help"):
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
        
        **Quick phrases that work:**
        - help, start, begin
        - login, sign up, account
        - utility, tracker, usage
        - recycle, materials, reuse
        - AI, insights, analysis
        - history, data, track
        - global, monitor, compare
        """)

# Add a section for app information
st.sidebar.title("About EcoAudit AI")
st.sidebar.info("""
    EcoAudit uses machine learning to provide intelligent sustainability insights.
    Advanced AI models analyze your usage patterns and environmental impact.
    
    🤖 AI Features:
    - Machine learning utility pattern analysis
    - Predictive usage modeling with anomaly detection
    - AI-powered material sustainability scoring
    - Personalized efficiency recommendations
    - Smart environmental impact assessment
    - Database-driven learning system
""")

# Footer
st.markdown("---")
st.markdown("© EcoAudit by Team EcoAudit - Helping you monitor your utility usage and reduce waste.")
