"""
Simple rule-based chatbot for EcoAudit app
Provides help and guidance without requiring external APIs
"""

import re
import random
from datetime import datetime
from difflib import SequenceMatcher
import database as db

class EcoAuditChatbot:
    def __init__(self):
        self.conversation_state = "greeting"
        self.user_name = None
        
        # Enhanced keyword matching with synonyms and environmental intelligence
        self.command_keywords = {
            'login': ['login', 'log in', 'signin', 'sign in', 'logon', 'log on', 'loging', 'loggin', 'acount', 'account'],
            'signup': ['signup', 'sign up', 'register', 'create account', 'new account', 'make account', 'sinup', 'singup', 'regester'],
            'utility': ['utility', 'usage', 'tracker', 'water', 'electricity', 'gas', 'electric', 'utilty', 'usege', 'trackr'],
            'recycle': ['recycle', 'recycling', 'material', 'reuse', 'recyling', 'recicle', 'matrial', 'reuing'],
            'ai': ['ai', 'insights', 'analysis', 'smart', 'artificial', 'intelligent', 'analisis', 'analisys'],
            'history': ['history', 'track', 'data', 'records', 'past', 'histroy', 'hitory', 'trak'],
            'global': ['global', 'monitor', 'compare', 'community', 'others', 'public', 'globel', 'moniter'],
            'help': ['help', 'support', 'guide', 'how', 'what', 'assist', 'halp', 'hep'],
            'profile': ['profile', 'update', 'edit', 'change', 'modify', 'settings', 'profil', 'updat'],
            'problem': ['problem', 'error', 'issue', 'bug', 'trouble', 'not working', 'broken', 'problm', 'eror'],
            'ranking': ['ranking', 'rank', 'competition', 'compete', 'champion', 'leaderboard', 'position', 'place', 'score', 'points'],
            'environmental': ['environmental', 'eco', 'green', 'sustainability', 'carbon', 'footprint', 'climate', 'conservation'],
            'tips': ['tips', 'advice', 'suggestions', 'recommendations', 'guidance', 'best practices', 'ways to improve'],
            'energy_saving': ['energy saving', 'save energy', 'reduce consumption', 'lower bills', 'efficient appliances', 'led lights', 'insulation'],
            'water_conservation': ['water conservation', 'save water', 'reduce water usage', 'fix leaks', 'low flow', 'drought', 'conservation'],
            'renewable_energy': ['renewable energy', 'solar power', 'wind energy', 'clean energy', 'sustainable energy', 'green energy'],
            'climate_change': ['climate change', 'global warming', 'greenhouse gases', 'emissions', 'carbon dioxide', 'methane'],
            'waste_reduction': ['waste reduction', 'zero waste', 'minimize waste', 'composting', 'food waste', 'packaging'],
            'sustainable_living': ['sustainable living', 'eco friendly', 'green lifestyle', 'environmentally conscious', 'sustainable practices']
        }
        
        # Initialize patterns after keyword setup
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        # Define response patterns with fuzzy matching capability
        self.patterns = {
            'greeting': [
                (r'(hello|hi|hey|good morning|good afternoon|good evening|helo|hii)', self.greeting_response),
                (r'(start|begin|help|halp)', self.help_response),
            ],
            'general': [
                # Enhanced pattern matching with ranking and environmental intelligence
                (r'(ranking|rank|leaderboard|competition|compete|champion|position|place)', self.ranking_help),
                (r'(who is rank 1|who is number 1|who is first|global champion|top user|leader)', self.get_global_rankings_info),
                (r'(current rankings|top rankings|who is winning|leaderboard now)', self.get_global_rankings_info),
                (r'(points|score|sustainability points|earn points|get points)', self.points_help),
                (r'(environmental class|eco class|green class|sustainability level)', self.environmental_class_help),
                
                # Advanced environmental knowledge patterns
                (r'(energy saving|save energy|reduce consumption|lower bills|efficient appliances|led lights|insulation)', self.energy_saving_help),
                (r'(water conservation|save water|reduce water usage|fix leaks|low flow|drought)', self.water_conservation_help),
                (r'(renewable energy|solar power|wind energy|clean energy|sustainable energy|green energy)', self.renewable_energy_help),
                (r'(climate change|global warming|greenhouse gases|emissions|carbon dioxide|methane)', self.climate_change_help),
                (r'(waste reduction|zero waste|minimize waste|composting|food waste|packaging)', self.waste_reduction_help),
                (r'(sustainable living|eco friendly|green lifestyle|environmentally conscious)', self.sustainable_living_help),
                
                # Existing patterns
                (r'(how to improve|tips|reduce usage|conserve|be green)', self.improvement_tips_help),
                (r'(carbon footprint|emissions|climate impact|environmental impact)', self.carbon_footprint_help),
                (r'(public account|private account|visibility|global monitor)', self.account_visibility_help),
                (r'(login|log in|sign in|account|acount|loging|loggin)', self.login_help),
                (r'(sign up|register|create account|new account|sinup|singup|regester)', self.signup_help),
                (r'(forgot|password|username|forgott|pasword)', self.forgot_help),
                (r'(utility|usage|tracker|water|electricity|gas|utilty|usege|trackr)', self.utility_help),
                (r'(recycle|recycling|material|reuse|recyling|recicle|matrial)', self.recycling_help),
                (r'(ai|insights|analysis|dashboard|smart|analisis)', self.ai_help),
                (r'(history|track|data|records|histroy|trak)', self.history_help),
                (r'(global|monitor|compare|community|globel|moniter)', self.global_monitor_help),
                (r'(profile|update|edit|change|settings|profil|updat)', self.profile_help),
                (r'(what|how|why|when|where|wat|howe)', self.general_question),
                (r'(thank|thanks|bye|goodbye|thanx|goodby)', self.goodbye_response),
                (r'(problem|error|issue|not working|broken|problm|eror)', self.troubleshoot_help),
                (r'(language|translate|español|français|deutsch|languag)', self.language_help),
            ]
        }
        
        # Default responses when no pattern matches
        self.default_responses = [
            "I'm here to help! You can ask me about:",
            "• How to create an account or log in",
            "• Using the utility tracker",
            "• Finding recycling tips",
            "• Understanding AI insights",
            "• Viewing your usage history",
            "• Comparing with global data",
            "",
            "What would you like to know more about?"
        ]

    def similarity(self, a, b):
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a, b).ratio()
    
    def fuzzy_command_match(self, user_input):
        """Find the best matching command using fuzzy matching"""
        user_input_clean = re.sub(r'[^\w\s]', '', user_input.lower())
        best_match = None
        best_score = 0.0
        
        for command, keywords in self.command_keywords.items():
            for keyword in keywords:
                # Direct substring match gets high score
                if keyword in user_input_clean:
                    return command, 1.0
                
                # Fuzzy matching for typos
                for word in user_input_clean.split():
                    similarity_score = self.similarity(word, keyword)
                    if similarity_score > 0.7 and similarity_score > best_score:
                        best_match = command
                        best_score = similarity_score
        
        return best_match, best_score
    
    def smart_default_response(self, user_input):
        """Provide contextual suggestions when no match is found"""
        suggestions = []
        
        # Analyze user input for partial matches
        if any(word in user_input for word in ['create', 'make', 'new']):
            suggestions.append("• To create an account: Go to User Profile > Create Account tab")
        
        if any(word in user_input for word in ['track', 'usage', 'utility']):
            suggestions.append("• To track utility usage: Log in and use the Utility Usage Tracker")
        
        if any(word in user_input for word in ['data', 'history', 'past']):
            suggestions.append("• To view your data: Check 'My History' after logging in")
        
        if any(word in user_input for word in ['compare', 'others', 'community']):
            suggestions.append("• To compare with others: Visit the Global Monitor section")
        
        response = "I understand you're asking about EcoAudit. Here are some helpful suggestions:\n\n"
        
        if suggestions:
            response += "\n".join(suggestions) + "\n\n"
        
        response += "**Common Commands:**\n"
        response += "• 'how to login' - Account access help\n"
        response += "• 'track utilities' - Usage monitoring guide\n"
        response += "• 'recycling tips' - Material guidance\n"
        response += "• 'view history' - Data tracking help\n"
        response += "• 'update profile' - Account management\n\n"
        response += "What specific task would you like help with?"
        
        return response
    
    def get_response(self, user_input):
        """Get chatbot response based on user input with enhanced intelligence"""
        try:
            if not user_input:
                return "Hi! How can I help you with EcoAudit today?"
            
            user_input = str(user_input).lower().strip()
            
            # Remove extra punctuation and normalize
            user_input_clean = re.sub(r'[!@#$%^&*()_+=\[\]{};:"\\|,.<>/?]+', ' ', user_input)
            user_input_clean = re.sub(r'\s+', ' ', user_input_clean).strip()
            
            # Check patterns based on conversation state
            if self.conversation_state == "greeting":
                patterns = self.patterns['greeting'] + self.patterns['general']
            else:
                patterns = self.patterns['general']
            
            # Try pattern matching first with better error handling
            for pattern, response_func in patterns:
                try:
                    if re.search(pattern, user_input_clean):
                        response = response_func(user_input)
                        if response and len(response.strip()) > 0:
                            return response
                except Exception:
                    continue
            
            # Try fuzzy command matching for misspellings and partial matches
            try:
                command, confidence = self.fuzzy_command_match(user_input_clean)
                if command and confidence > 0.6:
                    response = None
                    try:
                        if command == 'login':
                            response = self.login_help(user_input)
                        elif command == 'signup':
                            response = self.signup_help(user_input)
                        elif command == 'utility':
                            response = self.utility_help(user_input)
                        elif command == 'recycle':
                            response = self.recycling_help(user_input)
                        elif command == 'ai':
                            response = self.ai_help(user_input)
                        elif command == 'history':
                            response = self.history_help(user_input)
                        elif command == 'global':
                            response = self.global_monitor_help(user_input)
                        elif command == 'ranking':
                            response = self.get_global_rankings_info(user_input)
                        elif command == 'profile':
                            response = self.profile_help(user_input)
                        elif command == 'help':
                            response = self.help_response(user_input)
                        elif command == 'problem':
                            response = self.troubleshoot_help(user_input)
                        
                        if response and len(response.strip()) > 0:
                            return response
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Enhanced default response with contextual suggestions
            try:
                return self.smart_default_response(user_input_clean)
            except Exception:
                return "I'm here to help with EcoAudit! Ask me about creating accounts, tracking utilities, or recycling tips."
        
        except Exception:
            return "Hi! I'm Blinkbot, your EcoAudit assistant. How can I help you today?"

    def greeting_response(self, user_input):
        """Initial greeting response"""
        try:
            self.conversation_state = "chatting"
            return """Hi! Welcome to EcoAudit!

I'm Blinkbot, your helpful assistant for navigating the EcoAudit app.

**About EcoAudit:**
EcoAudit is your personal environmental impact tracker and sustainability companion. Monitor your utility consumption (water, electricity, gas), get smart recycling guidance for any material, and receive AI-powered insights to reduce your environmental footprint. Join a global community of environmentally conscious users working together toward a sustainable future.

**Navigation Guide:**

🏠 **Home Page** - Main dashboard with quick overview of your environmental impact

👤 **User Profile** - Create account or login to access personalized features

📊 **Utility Usage Tracker** - Add your monthly water, electricity, and gas consumption data

📈 **My History** - View your past usage patterns and track improvements over time

🤖 **AI Insights Dashboard** - Get personalized recommendations based on your usage patterns

♻️ **Materials Recycling Guide** - Find reuse and recycling tips for any material

🌍 **Global Monitor** - Compare your usage with other community members worldwide

❓ **Help Center** - Get assistance and chat with me for any questions

**Quick Start Tips:**
- New users: Click "User Profile" → "Create Account" 
- Existing users: Click "User Profile" → "Login"
- To track usage: Go to "Utility Usage Tracker" 
- For recycling help: Visit "Materials Recycling Guide"

What would you like to help you with today?"""
        except Exception:
            return "Hi! Welcome to EcoAudit! I'm Blinkbot, your helpful assistant. How can I help you today?"

    def help_response(self, user_input):
        """General help response"""
        try:
            self.conversation_state = "chatting"
            return """Here's how to use EcoAudit:

**Main Features:**
1. **User Profile** - Create account or log in
2. **Utility Usage Tracker** - Monitor water, electricity, and gas usage
3. **Materials Recycling Guide** - Get tips for reusing and recycling items
4. **AI Insights Dashboard** - View personalized recommendations
5. **My History** - Track your usage patterns over time
6. **Global Monitor** - Compare with other users' data

**Getting Started:**
Navigate using the menu on the left. Start by creating an account to unlock personal tracking features!

What specific feature would you like to learn about?"""
        except Exception:
            return "EcoAudit helps you track utility usage and get recycling tips. Create an account to start tracking your environmental impact!"

    def login_help(self, user_input):
        """Help with login process"""
        return """**How to Log In:**

1. Go to **User Profile** in the navigation menu
2. Click the **Login** tab
3. Enter your username
4. Click **Login**

**Don't have an account yet?**
Switch to the **Create Account** tab to sign up!

**Having trouble?**
Make sure you're using the exact username you registered with. Usernames are case-sensitive."""

    def profile_help(self, user_input):
        """Help with profile management"""
        return """**Profile Management & Updates:**

**Update Your Account:**
1. Go to **User Profile** in the navigation menu
2. Log in to your account
3. Use the **Update Profile** section to modify:
   • Household composition (adults, children, seniors)
   • Location and climate information
   • Housing type and energy features
   • Language preferences
   • Data visibility (public/private)

**Account Types:**
• **Public accounts** - Your data appears in Global Monitor for community comparison
• **Private accounts** - Your data remains personal and secure
• You can create both a public AND private account with the same username

**Managing Your Data:**
• View your usage statistics and environmental class
• Generate AI analysis of your consumption patterns
• Download your historical data
• Control data sharing preferences

**Profile Statistics:**
• Total usage records tracked
• Average monthly consumption
• Environmental impact classification
• Membership duration

Need help with a specific profile setting? Ask me about it!"""

    def signup_help(self, user_input):
        """Help with account creation"""
        return """**How to Create an Account:**

1. Go to **User Profile** in the navigation menu
2. Click the **Create Account** tab
3. Fill in your details:
   • Username (required) - can be used for both public and private accounts
   • Email (optional)
   • Language preference
   • Location and household information
   • Housing details
4. Choose account type: **Public** (data shared) or **Private** (data personal)
5. Click **Create Account**

**Important:** You can create BOTH a public and private account with the same username for different purposes.

**Why provide household details?**
This helps our AI give you more accurate usage comparisons and personalized recommendations based on your specific living situation!"""

    def utility_help(self, user_input):
        """Help with utility tracking"""
        return """**Utility Usage Tracker:**

Track your monthly consumption of:
• **Water** (in gallons)
• **Electricity** (in kWh) 
• **Gas** (in cubic meters)

**Features:**
• AI-powered usage assessment
• Efficiency scoring
• Personalized recommendations
• Historical tracking
• Carbon footprint calculation

**Note:** You need to be logged in to save your usage data and access AI insights."""

    def recycling_help(self, user_input):
        """Help with recycling features"""
        return """**Materials Recycling Guide:**

Enter any material name to get:
• **Reuse tips** - Creative ways to repurpose items
• **Recycling instructions** - Proper disposal methods
• **AI sustainability scoring** - Environmental impact analysis

**Popular materials people search for:**
• Plastic bottles, bags, containers
• Electronics and batteries
• Glass and metal items
• Paper and cardboard
• Clothing and textiles

**No login required** for this feature!"""

    def ai_help(self, user_input):
        """Help with AI features"""
        return """**AI Insights Dashboard:**

Our AI analyzes your data to provide:
• **Usage pattern analysis** - Identify trends and anomalies
• **Predictive modeling** - Forecast future consumption
• **Efficiency recommendations** - Personalized tips to reduce usage
• **Environmental impact assessment** - Your carbon footprint
• **Comparative analysis** - How you compare to similar households

**Requirements:**
• Must be logged in
• Need some usage history for accurate insights"""

    def history_help(self, user_input):
        """Help with usage history"""
        return """**My History:**

View and analyze your past utility usage:
• **Usage trends** over time
• **Monthly comparisons**
• **Efficiency scores** tracking
• **AI insights** evolution
• **Data visualization** with charts

You can filter by time periods and export your data.

**Note:** Only available for logged-in users with saved usage data."""

    def global_monitor_help(self, user_input):
        """Help with global monitor"""
        return """**Global Monitor:**

Compare your usage with other EcoAudit users:
• **Aggregated statistics** from public profiles
• **Environmental class rankings** (A, B, C)
• **Regional comparisons** by location type
• **Household size comparisons**
• **Download community data** for analysis

**Privacy:** Only users who choose "public" data visibility are included.

**Available to everyone** - no login required!"""

    def language_help(self, user_input):
        """Help with language options"""
        return """**Language Support:**

When creating an account, you can select your preferred language from:
• English
• Spanish (Español)
• French (Français)
• German (Deutsch)
• Chinese (中文)
• Japanese (日本語)
• Portuguese (Português)
• Italian (Italiano)

**Note:** Language preference is currently used for account settings. The main interface is in English, but we're working on full multilingual support!"""

    def troubleshoot_help(self, user_input):
        """Help with common problems"""
        return """**Common Issues & Solutions:**

**Can't log in?**
• Check username spelling (case-sensitive)
• Try creating an account if you haven't already

**Data not saving?**
• Make sure you're logged in
• Check your internet connection

**AI insights not showing?**
• You need some usage history first
• Try entering a few months of data

**Page not loading?**
• Refresh your browser
• Try a different browser if issues persist

**Still having problems?**
The app is designed to be simple and user-friendly. Most features work without special setup!"""

    def general_question(self, user_input):
        """Handle general questions"""
        if 'what' in user_input:
            return """EcoAudit is an environmental monitoring app that helps you:
• Track utility usage (water, electricity, gas)
• Get recycling and reuse tips for materials
• Receive AI-powered efficiency recommendations
• Compare your impact with other users

Ask me about any specific feature you'd like to learn about!"""
        elif 'how' in user_input:
            return """You can use EcoAudit by:
1. Creating an account (optional but recommended)
2. Entering your utility usage data
3. Getting materials recycling tips
4. Viewing AI insights and recommendations
5. Tracking your progress over time

What specific task would you like help with?"""
        else:
            return "\n".join(self.default_responses)

    def goodbye_response(self, user_input):
        """Farewell response"""
        responses = [
            "You're welcome! Happy to help you on your sustainability journey!",
            "Thanks for using EcoAudit! Every small step helps the environment.",
            "Goodbye! Remember, small changes make a big difference for our planet.",
            "Take care! Keep up the great work with your environmental monitoring!"
        ]
        return random.choice(responses)

    def forgot_help(self, user_input):
        """Help with forgotten credentials"""
        return """**Forgot Your Username?**

Since we don't store passwords, you just need your username to log in.

**If you forgot your username:**
• Try common variations you might have used
• Check if you wrote it down somewhere
• As a last resort, you can create a new account

**Tips for next time:**
• Choose a memorable username
• Write it down in a safe place
• Consider using your email address as username"""

    def ranking_help(self, user_input):
        """Help with environmental ranking and competition system"""
        return """🏆 **Environmental Champions Ranking System**

**How Rankings Work:**
• Earn points based on low utility usage (water, electricity, gas)
• Lower consumption = Higher points (up to 30 points per entry)
• Only public accounts can participate in rankings
• Real-time updates when you track usage

**Point System:**
• Excellent usage (very low): 10 points per utility type
• Good usage (moderate): 6-8 points per utility type
• Poor usage (high): 0-2 points per utility type

**Competition Features:**
• Global leaderboard with top 10 champions
• Your current rank and points displayed
• Compete to become Global Environmental Champion
• Rankings update automatically when you log usage

**To Join Rankings:**
1. Switch to a public account in User Profile
2. Track your utility usage regularly
3. Focus on reducing consumption to earn more points
4. Check Global Monitor to see your position

Would you like tips on how to improve your environmental performance?"""

    def points_help(self, user_input):
        """Help with sustainability points system"""
        return """⭐ **Sustainability Points System**

**How to Earn Points:**
• Track your utility usage in the tracker
• Points automatically calculated based on consumption levels
• Lower usage = More points earned

**Point Breakdown:**
**Water Usage (gallons/month):**
• ≤50: 5 points (Excellent)
• 51-100: 4 points (Very Good)
• 101-150: 3 points (Good)
• 151-200: 2 points (Fair)
• 201-300: 1 point (Poor)
• >300: 0 points (Needs Improvement)

**Electricity Usage (kWh/month):**
• ≤200: 5 points (Excellent)
• 201-400: 4 points (Very Good)
• 401-600: 3 points (Good)
• 601-800: 2 points (Fair)
• 801-1000: 1 point (Poor)
• >1000: 0 points (Needs Improvement)

**Gas Usage (m³/month):**
• ≤20: 5 points (Excellent)
• 21-40: 4 points (Very Good)
• 41-60: 3 points (Good)
• 61-80: 2 points (Fair)
• 81-100: 1 point (Poor)
• >100: 0 points (Needs Improvement)

**Maximum:** 15 points per usage entry (5 points per utility)
**Goal:** Consistently earn high points to climb rankings!"""

    def environmental_class_help(self, user_input):
        """Help with environmental classification system"""
        return """🌱 **Environmental Class System**

**Class A (Eco Champion):**
• Excellent utility usage across all categories
• Sustainable lifestyle practices
• Low carbon footprint
• Leading example for others

**Class B (Green Performer):**
• Good utility usage with room for improvement
• Moderate environmental impact
• Making progress toward sustainability

**Class C (Getting Started):**
• Higher utility usage levels
• Significant improvement opportunities
• Just beginning sustainability journey

**How Classification Works:**
• Based on your usage patterns over time
• Considers household size and location
• Updated automatically with new data
• AI analysis provides personalized insights

**Improving Your Class:**
• Reduce water, electricity, and gas consumption
• Implement energy-saving practices
• Track usage regularly to monitor progress
• Use AI recommendations for targeted improvements"""

    def improvement_tips_help(self, user_input):
        """Provide environmental improvement tips"""
        return """💡 **Environmental Improvement Tips**

**Water Conservation:**
• Fix leaks immediately
• Install low-flow showerheads and faucets
• Take shorter showers (5 minutes or less)
• Run dishwasher/washing machine only when full
• Collect rainwater for garden use

**Electricity Savings:**
• Switch to LED light bulbs
• Unplug devices when not in use
• Use smart thermostats
• Upgrade to energy-efficient appliances
• Use natural lighting during the day

**Gas Efficiency:**
• Improve home insulation
• Service heating systems regularly
• Lower thermostat by 2-3 degrees
• Use programmable thermostats
• Seal air leaks around windows/doors

**Advanced Tips:**
• Install solar panels if possible
• Use smart power strips
• Choose ENERGY STAR certified appliances
• Consider heat pumps for heating/cooling
• Plant trees for natural cooling

**Track Progress:**
• Monitor usage monthly in the tracker
• Watch your points increase as you improve
• Climb the environmental rankings
• Share achievements with the community"""

    def carbon_footprint_help(self, user_input):
        """Help with carbon footprint understanding"""
        return """🌍 **Carbon Footprint Information**

**What is Carbon Footprint:**
• Total greenhouse gas emissions from your activities
• Measured in CO2 equivalent
• Includes direct and indirect emissions
• Key factor in climate change impact

**Your Footprint Sources:**
• Electricity usage (coal/gas power plants)
• Natural gas heating/cooking
• Water heating and treatment
• Transportation and travel
• Food choices and consumption

**Footprint Categories:**
• **Low Impact:** <5 tons CO2/year
• **Moderate Impact:** 5-10 tons CO2/year
• **High Impact:** >10 tons CO2/year

**Reduction Strategies:**
• Use renewable energy sources
• Improve home energy efficiency
• Reduce meat consumption
• Use public transportation
• Buy local and seasonal products

**EcoAudit Tracking:**
• Automatically calculates based on utility usage
• Compares with household benchmarks
• Provides improvement recommendations
• Tracks progress over time

**Global Impact:**
• Average US household: 16 tons CO2/year
• Target for climate goals: <2 tons/year
• Every reduction makes a difference!"""

    def get_global_rankings_info(self, user_input):
        """Get current global rankings and champion information"""
        try:
            # Get top 5 rankings with proper error handling
            rankings = db.get_global_rankings(5)
            
            if rankings and len(rankings) > 0:
                response = "Current Global Environmental Champions:\n\n"
                
                for i, user in enumerate(rankings, 1):
                    try:
                        # Safe database attribute extraction using getattr
                        username = getattr(user, 'username', f"User{i}")
                        points = getattr(user, 'total_points', 0) or 0
                        location = getattr(user, 'location_type', 'Unknown') or 'Unknown'
                        env_class = getattr(user, 'environmental_class', 'N/A') or 'N/A'
                        
                        # Convert to safe types
                        username = str(username)
                        points = int(points) if isinstance(points, (int, float)) else 0
                        location = str(location)
                        env_class = str(env_class)
                        
                        if i == 1:
                            response += f"#{i} Global Champion: {username}\n"
                            response += f"   Points: {points}\n"
                            response += f"   Location: {location}\n"
                            response += f"   Environmental Class: {env_class}\n\n"
                        elif i == 2:
                            response += f"#{i} Runner-up: {username}\n"
                            response += f"   Points: {points}\n"
                            response += f"   Location: {location}\n\n"
                        elif i == 3:
                            response += f"#{i} Third Place: {username}\n"
                            response += f"   Points: {points}\n"
                            response += f"   Location: {location}\n\n"
                        else:
                            response += f"#{i} {username} - {points} points ({location})\n"
                    except Exception:
                        # Skip problematic entries instead of failing
                        continue
                
                response += "\nHow to compete:\n"
                response += "• Track your utility usage regularly\n"
                response += "• Keep consumption low to earn more points\n"
                response += "• Verify recycling activities for bonus points\n"
                response += "• Switch to public account to join rankings"
                
                return response
            else:
                return "No ranking data available yet. Be the first to start tracking your environmental impact!"
                
        except Exception:
            return "Rankings are currently being updated. Please check the Global Monitor page for the latest information."

    def account_visibility_help(self, user_input):
        """Help with account visibility and public/private settings"""
        return """👥 **Account Visibility Settings**

**Private Accounts:**
• Your data is completely private
• Not visible in Global Monitor
• Cannot participate in rankings
• Personal tracking only

**Public Accounts:**
• Data appears in Global Monitor
• Can participate in environmental rankings
• Compete for Global Champion status
• Help inspire others with your progress

**Privacy Protection:**
• Only environmental data is shared
• Personal information stays private
• Username and location type only
• No email or sensitive details shared

**Switching Visibility:**
1. Go to User Profile section
2. Click "Update Profile"
3. Change "Data Visibility" setting
4. Save changes to apply

**Benefits of Public:**
• Compete in global rankings
• Earn sustainability points
• Inspire others with your achievements
• Learn from community best practices

**Why Choose Public:**
• Make a positive impact
• Join the environmental movement
• Challenge yourself to improve
• Become an eco-leader!"""

    def energy_saving_help(self, user_input):
        """Comprehensive energy saving guidance"""
        return """⚡ Energy Saving Strategies

Immediate Actions:
• Switch to LED light bulbs (75% less energy)
• Unplug electronics when not in use
• Use power strips to eliminate standby power
• Set thermostat 2-3 degrees lower in winter
• Close curtains/blinds during hot days

Appliance Efficiency:
• Use cold water for washing clothes
• Air dry clothes instead of using dryer
• Keep refrigerator at 37-40°F
• Use microwave for small heating tasks
• Clean dryer lint after each use

Home Improvements:
• Add insulation to attic and walls
• Seal air leaks around windows/doors
• Install programmable thermostat
• Use ceiling fans to circulate air
• Consider energy-efficient windows

Track your energy consumption progress with EcoAudit's utility tracker!"""

    def water_conservation_help(self, user_input):
        """Water conservation guidance"""
        return """💧 Water Conservation Strategies

Bathroom (70% of home water use):
• Take 5-minute showers instead of baths
• Install low-flow showerheads
• Fix leaky faucets immediately
• Turn off water while brushing teeth
• Install dual-flush toilets

Kitchen & Laundry:
• Run dishwasher only when full
• Use cold water for washing clothes
• Fix dripping faucets promptly
• Scrape dishes instead of pre-rinsing

Outdoor Conservation:
• Water plants early morning or evening
• Use drought-resistant native plants
• Install drip irrigation systems
• Collect rainwater for garden use

Track your water usage with EcoAudit to see conservation progress!"""

    def renewable_energy_help(self, user_input):
        """Renewable energy information"""
        return """☀️ Renewable Energy Solutions

Solar Power Benefits:
• Reduces electricity bills by 50-90%
• Available tax credits and incentives
• Payback period typically 6-10 years
• Increases home value
• Low maintenance requirements

Getting Started:
• Get energy audit first
• Research local installers
• Compare financing options
• Check roof condition and orientation
• Understand net metering policies

Other Options:
• Small wind turbines for rural areas
• Geothermal heating/cooling systems
• Solar water heaters
• Community solar programs
• Green energy utility programs

Calculate your energy needs with EcoAudit first!"""

    def climate_change_help(self, user_input):
        """Climate change education"""
        return """🌍 Understanding Climate Change

What's Happening:
• Global temperatures rising due to greenhouse gases
• More frequent extreme weather events
• Sea levels rising, ice caps melting
• Ecosystems under stress worldwide

Personal Impact Actions:
• Reduce energy consumption at home
• Use public transport or electric vehicles
• Eat less meat, more plant-based foods
• Reduce, reuse, recycle materials
• Support renewable energy

Home Carbon Reduction:
• Improve home insulation
• Use energy-efficient appliances
• Switch to renewable energy
• Reduce water consumption
• Minimize waste production

Use EcoAudit to monitor your household emissions and track progress!"""

    def waste_reduction_help(self, user_input):
        """Waste reduction strategies"""
        return """♻️ Waste Reduction Strategies

The 5 R's Hierarchy:
1. Refuse - Say no to single-use items
2. Reduce - Buy only what you need
3. Reuse - Find new purposes for items
4. Recycle - Process materials into new products
5. Rot - Compost organic waste

Kitchen Waste Reduction:
• Plan meals to avoid food waste
• Store food properly to extend life
• Use leftovers creatively
• Compost food scraps
• Buy in bulk to reduce packaging

Household Strategies:
• Buy quality items that last longer
• Repair instead of replacing when possible
• Donate or sell unwanted items
• Choose products with minimal packaging
• Use reusable bags, bottles, and containers

Use EcoAudit's material guide to find proper disposal methods!"""

    def sustainable_living_help(self, user_input):
        """Sustainable living guidance"""
        return """🌱 Sustainable Living Guide

Sustainable Diet:
• Eat more plant-based meals
• Choose locally grown, seasonal produce
• Reduce meat consumption (especially beef)
• Minimize food waste
• Support organic farming practices

Eco-Friendly Transportation:
• Walk or bike for short trips
• Use public transportation
• Carpool or rideshare
• Consider electric or hybrid vehicles
• Work from home when possible

Sustainable Shopping:
• Buy quality items that last
• Choose secondhand when possible
• Support ethical and local businesses
• Read labels for environmental certifications
• Avoid fast fashion

Green Home Practices:
• Use natural cleaning products
• Minimize single-use plastics
• Install water-saving fixtures
• Choose sustainable materials for renovations
• Maintain and repair instead of replacing

Track your sustainable lifestyle progress with EcoAudit's monitoring tools!"""

# Initialize the chatbot
chatbot = EcoAuditChatbot()