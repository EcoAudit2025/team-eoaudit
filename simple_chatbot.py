"""
Simple rule-based chatbot for EcoAudit app
Provides help and guidance without requiring external APIs
"""

import re
import random
from datetime import datetime
from difflib import SequenceMatcher

class EcoAuditChatbot:
    def __init__(self):
        self.conversation_state = "greeting"
        self.user_name = None
        
        # Enhanced keyword matching with synonyms and common misspellings
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
            'problem': ['problem', 'error', 'issue', 'bug', 'trouble', 'not working', 'broken', 'problm', 'eror']
        }
        
        # Define response patterns with fuzzy matching capability
        self.patterns = {
            'greeting': [
                (r'(hello|hi|hey|good morning|good afternoon|good evening|helo|hii)', self.greeting_response),
                (r'(start|begin|help|halp)', self.help_response),
            ],
            'general': [
                # Enhanced pattern matching
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
            
            # Try pattern matching first
            for pattern, response_func in patterns:
                try:
                    if re.search(pattern, user_input_clean):
                        return response_func(user_input)
                except Exception:
                    continue
            
            # Try fuzzy command matching for misspellings and partial matches
            try:
                command, confidence = self.fuzzy_command_match(user_input_clean)
                if command and confidence > 0.6:
                    if command == 'login':
                        return self.login_help(user_input)
                    elif command == 'signup':
                        return self.signup_help(user_input)
                    elif command == 'utility':
                        return self.utility_help(user_input)
                    elif command == 'recycle':
                        return self.recycling_help(user_input)
                    elif command == 'ai':
                        return self.ai_help(user_input)
                    elif command == 'history':
                        return self.history_help(user_input)
                    elif command == 'global':
                        return self.global_monitor_help(user_input)
                    elif command == 'profile':
                        return self.profile_help(user_input)
                    elif command == 'help':
                        return self.help_response(user_input)
                    elif command == 'problem':
                        return self.troubleshoot_help(user_input)
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
EcoAudit helps you monitor your utility usage (water, electricity, gas) and provides smart recycling guidance for materials. Our AI system analyzes your consumption patterns and gives personalized recommendations to reduce your environmental impact.

**Getting Started:**
• **New here?** Create an account in the User Profile section to start tracking your usage
• **Returning user?** Log in to access your personal dashboard and history
• **Just exploring?** You can use the Materials Recycling Guide and view global data without an account

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

# Initialize the chatbot
chatbot = EcoAuditChatbot()