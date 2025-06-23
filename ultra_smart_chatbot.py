"""
Ultra Smart EcoBot - Enhanced AI Chatbot for EcoAudit
Provides comprehensive environmental knowledge and smart responses
Analyzes global monitor data and user patterns for contextual insights
"""

import re
import json
from datetime import datetime, timedelta
import database as db
try:
    from fuzzywuzzy import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    def fuzz_ratio(a, b):
        return 50  # fallback

class UltraSmartEcoBot:
    def __init__(self):
        self.name = "Blink - Ultra Smart EcoBot"
        self.conversation_context = []
        self.user_context = {}
        self.global_insights = {}
        self.environmental_knowledge = self._load_comprehensive_knowledge()
        self.app_knowledge = self._load_app_knowledge()
        self.personality_traits = {
            'helpful': True,
            'educational': True,
            'encouraging': True,
            'precise': True,
            'adaptive': True,
            'friendly': True
        }
        
    def _load_comprehensive_knowledge(self):
        """Load comprehensive environmental knowledge base"""
        return {
            "fundamentals": {
                "conservation": "Protect and preserve natural resources for future generations through responsible use and management.",
                "sustainability": "Meet present needs without compromising the ability of future generations to meet their own needs.",
                "renewable_energy": "Transition to clean, renewable energy sources like solar, wind, and hydroelectric power.",
                "waste_reduction": "Minimize waste generation through reduce, reuse, recycle, and refuse principles.",
                "water_conservation": "Protect freshwater resources through efficient use and pollution prevention.",
                "biodiversity": "Maintain ecosystem diversity to ensure natural balance and species survival.",
                "carbon_footprint": "Reduce greenhouse gas emissions to combat climate change.",
                "circular_economy": "Design out waste and keep products and materials in use for as long as possible.",
                "environmental_justice": "Ensure fair treatment and meaningful involvement of all people in environmental decisions.",
                "precautionary_principle": "Take preventive action in the face of uncertainty about environmental harm.",
                "ecosystem_services": "Recognize and protect the benefits that ecosystems provide to humanity.",
                "life_cycle_thinking": "Consider environmental impacts throughout a product's entire life cycle.",
                "pollution_prevention": "Prevent pollution at the source rather than treating it after it occurs.",
                "environmental_education": "Increase awareness and understanding of environmental issues and solutions."
            },
            "climate_change": {
                "causes": ["Greenhouse gas emissions", "Deforestation", "Industrial processes", "Transportation", "Agriculture"],
                "effects": ["Rising temperatures", "Sea level rise", "Extreme weather", "Ecosystem disruption", "Food security threats"],
                "solutions": ["Renewable energy adoption", "Energy efficiency", "Carbon pricing", "Reforestation", "Sustainable transportation"]
            },
            "energy_efficiency": {
                "home_tips": ["LED lighting", "Smart thermostats", "Proper insulation", "Energy-efficient appliances", "Solar panels"],
                "water_saving": ["Low-flow fixtures", "Fix leaks promptly", "Rainwater harvesting", "Greywater systems", "Native landscaping"],
                "gas_conservation": ["Efficient heating systems", "Proper insulation", "Programmable thermostats", "Regular maintenance", "Zone heating"]
            },
            "recycling_guide": {
                "plastic": {
                    "recyclable": ["#1 PET bottles", "#2 HDPE containers", "#5 PP containers"],
                    "non_recyclable": ["#6 Polystyrene", "Mixed plastics", "Flexible films"],
                    "tips": "Clean containers, remove caps, check local guidelines"
                },
                "glass": {
                    "recyclable": ["Clear glass", "Brown glass", "Green glass"],
                    "non_recyclable": ["Mirrors", "Light bulbs", "Ceramics"],
                    "tips": "Remove caps, rinse clean, separate by color"
                },
                "metal": {
                    "recyclable": ["Aluminum cans", "Steel cans", "Copper wire"],
                    "non_recyclable": ["Paint cans with residue", "Aerosol cans"],
                    "tips": "Clean thoroughly, remove labels when possible"
                },
                "paper": {
                    "recyclable": ["Newspapers", "Magazines", "Cardboard"],
                    "non_recyclable": ["Wax paper", "Paper towels", "Shredded paper"],
                    "tips": "Keep dry, remove staples, flatten boxes"
                }
            }
        }
    
    def _load_app_knowledge(self):
        """Load EcoAudit app-specific knowledge"""
        return {
            "features": {
                "utility_tracking": "Track water, electricity, and gas usage with AI-powered analysis and recommendations",
                "materials_guide": "Smart recycling and reuse guidance with comprehensive material database",
                "ai_insights": "Advanced machine learning insights for usage prediction and optimization",
                "global_monitor": "Community rankings and comparative sustainability performance",
                "points_system": "Gamified sustainability scoring with environmental class ratings",
                "multilingual": "Support for multiple languages with personalized recommendations"
            },
            "scoring": {
                "water_points": "Up to 20 points per entry based on efficiency relative to household size",
                "electricity_points": "Up to 20 points per entry with peak usage optimization bonuses",
                "gas_points": "Up to 18 points per entry with seasonal adjustment factors",
                "efficiency_bonus": "Up to 25% additional points for exceptional efficiency",
                "recycling_points": "3 points per verified recycling activity"
            },
            "environmental_classes": {
                "A": "Excellent sustainability practices, top 20% of users",
                "B": "Good sustainability practices, middle 60% of users", 
                "C": "Developing sustainability practices, bottom 20% with improvement potential"
            },
            "usage_limits": {
                "daily_entries": "Maximum 2 utility usage entries per day per user",
                "material_searches": "Unlimited recycling guide searches",
                "verification_uploads": "Unlimited recycling verification submissions"
            }
        }
    
    def get_response(self, user_input, current_user=None):
        """Generate ultra-smart responses with comprehensive knowledge"""
        try:
            # Update conversation context
            self.conversation_context.append({
                'timestamp': datetime.now(),
                'input': user_input,
                'user_id': current_user.id if current_user else None
            })
            
            # Keep context manageable
            if len(self.conversation_context) > 10:
                self.conversation_context.pop(0)
            
            # Update user context
            if current_user:
                self.user_context = self._analyze_user_context(current_user)
            
            # Update global insights
            self._update_global_insights()
            
            # Clean and analyze input
            cleaned_input = self._clean_input(user_input)
            intent = self._analyze_intent_comprehensive(cleaned_input)
            entities = self._extract_entities_advanced(cleaned_input)
            
            # Generate response based on intent
            response = self._generate_smart_response(intent, entities, cleaned_input, current_user)
            
            return response
            
        except Exception as e:
            return self._intelligent_fallback(user_input)
    
    def _analyze_user_context(self, user):
        """Comprehensive user context analysis"""
        try:
            # Get user's usage history
            recent_usage = db.get_utility_history(user.id, limit=10)
            
            # Basic user info
            user_class = getattr(user, 'environmental_class', 'Unknown')
            total_points = getattr(user, 'total_points', 0)
            household_size = getattr(user, 'household_size', 1)
            location = getattr(user, 'location_type', 'Unknown')
            
            # Calculate trends and patterns
            performance_trend = self._calculate_performance_trend(recent_usage)
            usage_patterns = self._analyze_usage_patterns(recent_usage)
            
            return {
                'environmental_class': user_class,
                'total_points': total_points,
                'household_size': household_size,
                'location': location,
                'recent_usage_count': len(recent_usage),
                'performance_trend': performance_trend,
                'usage_patterns': usage_patterns,
                'strengths': self._identify_strengths(user, recent_usage),
                'improvement_areas': self._identify_improvements(user, recent_usage)
            }
            
        except Exception:
            return {}
    
    def _update_global_insights(self):
        """Update comprehensive global community insights"""
        try:
            # Get global rankings
            rankings = db.get_global_rankings(100)
            
            if rankings:
                total_users = len(rankings)
                avg_points = sum(user[1] for user in rankings) / total_users if total_users > 0 else 0
                
                # Analyze class distribution
                class_dist = {}
                for user in rankings:
                    user_class = user[2] if len(user) > 2 else 'Unknown'
                    class_dist[user_class] = class_dist.get(user_class, 0) + 1
                
                # Get top performers
                top_performers = rankings[:10]
                
                self.global_insights = {
                    'total_users': total_users,
                    'average_points': avg_points,
                    'class_distribution': class_dist,
                    'top_performers': top_performers,
                    'community_trend': 'improving'
                }
            
        except Exception:
            self.global_insights = {}
    
    def _analyze_intent_comprehensive(self, text):
        """Advanced intent analysis with comprehensive pattern matching"""
        text_lower = text.lower()
        
        # Enhanced intent patterns
        intent_patterns = {
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'good evening', 'start', 'greetings'],
            'utility_guidance': ['water', 'electricity', 'gas', 'usage', 'consumption', 'bill', 'meter', 'kwh', 'gallons', 'cubic'],
            'comparison': ['compare', 'vs', 'versus', 'better', 'worse', 'rank', 'position', 'leaderboard', 'standings'],
            'recommendations': ['suggest', 'recommend', 'advice', 'tips', 'help', 'improve', 'optimize', 'enhance'],
            'recycling': ['recycle', 'dispose', 'throw', 'waste', 'material', 'plastic', 'glass', 'metal', 'paper'],
            'points_scoring': ['points', 'score', 'rating', 'performance', 'level', 'class', 'grade'],
            'global_community': ['community', 'global', 'everyone', 'others', 'average', 'typical', 'users'],
            'environmental_education': ['environment', 'carbon', 'footprint', 'green', 'sustainable', 'eco', 'climate'],
            'app_features': ['feature', 'function', 'how to use', 'navigate', 'interface', 'dashboard'],
            'technical_support': ['error', 'bug', 'problem', 'not working', 'broken', 'issue', 'help'],
            'fundamentals': ['14', 'fundamental', 'principle', 'basic', 'foundation', 'core', 'essential'],
            'data_analysis': ['trend', 'pattern', 'analysis', 'insight', 'prediction', 'forecast']
        }
        
        # Score each intent
        intent_scores = {}
        for intent, keywords in intent_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 2
                elif FUZZY_AVAILABLE:
                    # Fuzzy matching for typos
                    words = text_lower.split()
                    for word in words:
                        ratio = fuzz.ratio(word, keyword)
                        if ratio > 80:
                            score += 1.5
                        elif ratio > 60:
                            score += 1
            intent_scores[intent] = score
        
        # Return highest scoring intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent
        
        return 'general_question'
    
    def _extract_entities_advanced(self, text):
        """Advanced entity extraction"""
        entities = {
            'materials': [],
            'utilities': [],
            'numbers': [],
            'locations': [],
            'time_expressions': []
        }
        
        # Material entities
        materials = ['plastic', 'glass', 'metal', 'paper', 'cardboard', 'aluminum', 'steel', 'electronics']
        for material in materials:
            if material in text.lower():
                entities['materials'].append(material)
        
        # Utility entities
        utilities = ['water', 'electricity', 'gas', 'energy', 'power']
        for utility in utilities:
            if utility in text.lower():
                entities['utilities'].append(utility)
        
        # Extract numbers
        numbers = re.findall(r'\d+\.?\d*', text)
        entities['numbers'] = [float(n) for n in numbers]
        
        return entities
    
    def _generate_smart_response(self, intent, entities, cleaned_input, current_user):
        """Generate comprehensive smart responses"""
        
        if intent == 'greeting':
            return self._greeting_response(current_user)
        
        elif intent == 'utility_guidance':
            return self._utility_guidance_response(entities)
        
        elif intent == 'comparison':
            return self._comparison_response()
        
        elif intent == 'recommendations':
            return self._recommendations_response()
        
        elif intent == 'recycling':
            return self._recycling_response(entities)
        
        elif intent == 'points_scoring':
            return self._points_response()
        
        elif intent == 'global_community':
            return self._global_community_response()
        
        elif intent == 'environmental_education':
            return self._environmental_education_response(cleaned_input)
        
        elif intent == 'app_features':
            return self._app_features_response(cleaned_input)
        
        elif intent == 'technical_support':
            return self._technical_support_response(cleaned_input)
        
        elif intent == 'fundamentals':
            return self._fundamentals_response()
        
        elif intent == 'data_analysis':
            return self._data_analysis_response()
        
        else:
            return self._comprehensive_general_response(cleaned_input)
    
    def _greeting_response(self, current_user):
        """Personalized greeting response"""
        base_greeting = "Hello! I'm your Ultra Smart EcoBot assistant, here to help you with all your environmental and sustainability questions."
        
        if current_user:
            user_class = getattr(current_user, 'environmental_class', 'Unknown')
            total_points = getattr(current_user, 'total_points', 0)
            
            if user_class == 'A':
                return f"{base_greeting}\n\nGreat to see you again! With your Class A rating and {total_points} points, you're truly leading the way in sustainability. How can I help you continue your excellent environmental stewardship today?"
            
            elif user_class == 'B':
                return f"{base_greeting}\n\nWelcome back! You're doing well with your Class B rating and {total_points} points. I'm here to help you optimize your sustainability practices even further."
            
            elif user_class == 'C':
                return f"{base_greeting}\n\nWelcome! I see you're building your sustainability journey with {total_points} points. I'm excited to help you discover new ways to improve your environmental impact."
        
        return f"{base_greeting}\n\nI can help you with:\n• Utility usage optimization\n• Recycling and waste management\n• Environmental education\n• Community comparisons\n• App features and navigation\n\nWhat would you like to explore today?"
    
    def _utility_guidance_response(self, entities):
        """Comprehensive utility guidance"""
        utilities = entities.get('utilities', [])
        response = "**Smart Utility Guidance:**\n\n"
        
        if 'water' in utilities or not utilities:
            response += "**Water Conservation:**\n"
            response += "• Install low-flow fixtures (save 25-60% on water usage)\n"
            response += "• Fix leaks immediately (one drop per second = 5 gallons/day)\n"
            response += "• Use efficient appliances (Energy Star rated)\n"
            response += "• Collect rainwater for gardens\n"
            response += "• Take shorter showers (4-5 minutes optimal)\n\n"
        
        if 'electricity' in utilities or not utilities:
            response += "**Electricity Optimization:**\n"
            response += "• Switch to LED bulbs (80% energy savings)\n"
            response += "• Use smart power strips to eliminate phantom loads\n"
            response += "• Optimize thermostat settings (78°F summer, 68°F winter)\n"
            response += "• Unplug devices when not in use\n"
            response += "• Use natural light during day\n\n"
        
        if 'gas' in utilities or not utilities:
            response += "**Gas Conservation:**\n"
            response += "• Maintain heating systems annually\n"
            response += "• Seal air leaks around windows and doors\n"
            response += "• Use programmable thermostats\n"
            response += "• Insulate water heater and pipes\n"
            response += "• Consider zone heating for efficiency\n\n"
        
        response += "**EcoAudit Integration:**\n"
        response += "Track your improvements in our utility monitoring section and watch your environmental class improve!"
        
        return response
    
    def _comparison_response(self):
        """Community comparison insights"""
        if not self.global_insights:
            return "I'm gathering community data for comparisons. Please check back shortly for comprehensive community insights."
        
        total_users = self.global_insights.get('total_users', 0)
        avg_points = self.global_insights.get('average_points', 0)
        class_dist = self.global_insights.get('class_distribution', {})
        
        response = f"**Community Comparison Insights:**\n\n"
        response += f"**Active Community:** {total_users} sustainability champions\n"
        response += f"**Average Score:** {avg_points:.1f} points\n\n"
        
        response += "**Performance Distribution:**\n"
        for env_class, count in class_dist.items():
            percentage = (count / total_users) * 100 if total_users > 0 else 0
            if env_class == 'A':
                response += f"• Class A (Excellent): {count} users ({percentage:.1f}%) - Top performers\n"
            elif env_class == 'B':
                response += f"• Class B (Good): {count} users ({percentage:.1f}%) - Solid sustainability practices\n"
            elif env_class == 'C':
                response += f"• Class C (Developing): {count} users ({percentage:.1f}%) - Great improvement potential\n"
        
        if self.user_context:
            user_points = self.user_context.get('total_points', 0)
            if user_points > avg_points:
                difference = user_points - avg_points
                response += f"\n**Your Performance:** {difference:.1f} points above community average! You're performing excellently compared to other users."
            else:
                difference = avg_points - user_points
                response += f"\n**Growth Opportunity:** {difference:.1f} points below average. Focus on consistent tracking and optimization to improve your ranking."
        
        return response
    
    def _recycling_response(self, entities):
        """Comprehensive recycling guidance"""
        materials = entities.get('materials', [])
        
        response = "**Comprehensive Recycling Guide:**\n\n"
        
        if materials:
            for material in materials:
                if material in self.environmental_knowledge['recycling_guide']:
                    guide = self.environmental_knowledge['recycling_guide'][material]
                    response += f"**{material.title()} Recycling:**\n"
                    response += f"• Recyclable: {', '.join(guide['recyclable'])}\n"
                    response += f"• Non-recyclable: {', '.join(guide['non_recyclable'])}\n"
                    response += f"• Tips: {guide['tips']}\n\n"
        else:
            # General recycling guidance
            response += "**General Recycling Best Practices:**\n"
            response += "• Clean containers before recycling\n"
            response += "• Check local recycling guidelines\n"
            response += "• Separate materials by type\n"
            response += "• Remove caps and labels when required\n"
            response += "• Never wishcycle (put non-recyclables in recycling)\n\n"
            
            response += "**Material Categories:**\n"
            for material, guide in self.environmental_knowledge['recycling_guide'].items():
                response += f"• {material.title()}: {guide['tips']}\n"
        
        response += "\n**EcoAudit Feature:** Use our Materials Guide for specific recycling instructions and earn points through our verification system!"
        
        return response
    
    def _environmental_education_response(self, text):
        """Comprehensive environmental education"""
        # Check for specific topics
        if '14' in text or 'fundamental' in text:
            return self._fundamentals_response()
        
        if 'climate' in text:
            climate = self.environmental_knowledge['climate_change']
            response = "**Climate Change Education:**\n\n"
            response += f"**Main Causes:** {', '.join(climate['causes'])}\n\n"
            response += f"**Primary Effects:** {', '.join(climate['effects'])}\n\n"
            response += f"**Solutions:** {', '.join(climate['solutions'])}\n\n"
            response += "**Your Role:** Every sustainability action you take contributes to climate solution. Track your impact with EcoAudit!"
            return response
        
        # General environmental education
        response = "**Environmental Education Hub:**\n\n"
        response += "**Key Topics I Can Teach:**\n"
        response += "• The 14 Fundamental Environmental Principles\n"
        response += "• Climate Change Science and Solutions\n"
        response += "• Energy Efficiency and Conservation\n"
        response += "• Waste Reduction and Recycling\n"
        response += "• Water Conservation Strategies\n"
        response += "• Sustainable Living Practices\n"
        response += "• Carbon Footprint Reduction\n"
        response += "• Biodiversity and Ecosystem Protection\n\n"
        response += "Ask me about any specific environmental topic, and I'll provide comprehensive, science-based information!"
        
        return response
    
    def _fundamentals_response(self):
        """The 14 fundamental environmental principles"""
        fundamentals = self.environmental_knowledge['fundamentals']
        
        response = "**The 14 Fundamental Environmental Principles:**\n\n"
        
        for i, (key, value) in enumerate(fundamentals.items(), 1):
            principle_name = key.replace('_', ' ').title()
            response += f"**{i}. {principle_name}**\n{value}\n\n"
        
        response += "**Application in EcoAudit:**\nOur platform helps you apply these principles through practical utility tracking, recycling guidance, and community engagement. Each feature is designed around these core environmental concepts."
        
        return response
    
    def _app_features_response(self, text):
        """Comprehensive app features explanation"""
        features = self.app_knowledge['features']
        
        response = "**EcoAudit Features Guide:**\n\n"
        
        for feature, description in features.items():
            feature_name = feature.replace('_', ' ').title()
            response += f"**{feature_name}:** {description}\n\n"
        
        response += "**How to Get Started:**\n"
        response += "1. Create your account (public or private)\n"
        response += "2. Enter your household information\n"
        response += "3. Start tracking utility usage\n"
        response += "4. Explore recycling guidance\n"
        response += "5. Review AI insights and recommendations\n"
        response += "6. Compare with global community\n\n"
        
        response += "**Scoring System:**\n"
        scoring = self.app_knowledge['scoring']
        for score_type, description in scoring.items():
            score_name = score_type.replace('_', ' ').title()
            response += f"• {score_name}: {description}\n"
        
        return response
    
    def _technical_support_response(self, text):
        """Technical support and troubleshooting"""
        response = "**Technical Support & Troubleshooting:**\n\n"
        
        if 'not working' in text or 'broken' in text:
            response += "**Common Issues & Solutions:**\n"
            response += "• **Data not saving:** Ensure you're logged in and have internet connection\n"
            response += "• **AI insights missing:** You need at least 3 usage entries for analysis\n"
            response += "• **Points not updating:** Check daily usage limits (2 entries per day)\n"
            response += "• **Page loading slowly:** Try refreshing or clearing browser cache\n\n"
        
        response += "**App Requirements:**\n"
        response += "• Modern web browser (Chrome, Firefox, Safari, Edge)\n"
        response += "• Internet connection for data synchronization\n"
        response += "• JavaScript enabled\n\n"
        
        response += "**Getting Help:**\n"
        response += "• Use this chat for immediate assistance\n"
        response += "• Check app features guide for usage instructions\n"
        response += "• Review environmental education for background knowledge\n"
        response += "• All features are designed to be intuitive and user-friendly\n\n"
        
        response += "**Data Privacy:**\n"
        response += "• Your private data is secure and not shared\n"
        response += "• Public accounts only show anonymized rankings\n"
        response += "• You control your privacy settings\n"
        
        return response
    
    def _comprehensive_general_response(self, text):
        """Comprehensive fallback response"""
        response = "I understand you're asking about environmental sustainability and EcoAudit. Here's how I can help:\n\n"
        
        response += "**Environmental Knowledge:**\n"
        response += "• Climate change science and solutions\n"
        response += "• The 14 fundamental environmental principles\n"
        response += "• Energy, water, and gas conservation strategies\n"
        response += "• Comprehensive recycling and waste management\n\n"
        
        response += "**EcoAudit Expertise:**\n"
        response += "• Utility usage tracking and optimization\n"
        response += "• Points system and environmental classifications\n"
        response += "• Community comparisons and global insights\n"
        response += "• AI-powered recommendations and predictions\n"
        response += "• Materials recycling guidance\n\n"
        
        response += "**Ask me anything about:**\n"
        response += "• How to improve your sustainability score\n"
        response += "• Specific environmental topics or concerns\n"
        response += "• App features and navigation\n"
        response += "• Community comparisons and benchmarking\n"
        response += "• Technical support and troubleshooting\n\n"
        
        response += f"What specific aspect would you like to explore? I have comprehensive knowledge about environmental science and this application."
        
        return response
    
    def _clean_input(self, text):
        """Clean and normalize input text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def _calculate_performance_trend(self, usage_data):
        """Calculate user performance trend"""
        if len(usage_data) < 2:
            return 'insufficient_data'
        
        # Simple trend analysis based on points
        recent_points = [entry.points_earned for entry in usage_data[-3:] if hasattr(entry, 'points_earned')]
        older_points = [entry.points_earned for entry in usage_data[-6:-3] if hasattr(entry, 'points_earned')]
        
        if recent_points and older_points:
            recent_avg = sum(recent_points) / len(recent_points)
            older_avg = sum(older_points) / len(older_points)
            
            if recent_avg > older_avg:
                return 'improving'
            elif recent_avg < older_avg:
                return 'declining'
            else:
                return 'stable'
        
        return 'insufficient_data'
    
    def _analyze_usage_patterns(self, usage_data):
        """Analyze user usage patterns"""
        if not usage_data:
            return {}
        
        patterns = {
            'consistency': len(usage_data) > 5,
            'recent_activity': len([u for u in usage_data if (datetime.now() - u.timestamp).days < 7]) > 0,
            'total_entries': len(usage_data)
        }
        
        return patterns
    
    def _identify_strengths(self, user, usage_data):
        """Identify user strengths"""
        strengths = []
        
        user_class = getattr(user, 'environmental_class', 'Unknown')
        if user_class == 'A':
            strengths.append('Excellent overall sustainability practices')
        elif user_class == 'B':
            strengths.append('Good sustainability foundation')
        
        if len(usage_data) > 10:
            strengths.append('Consistent tracking and monitoring')
        
        return strengths
    
    def _identify_improvements(self, user, usage_data):
        """Identify improvement areas"""
        improvements = []
        
        user_class = getattr(user, 'environmental_class', 'Unknown')
        if user_class in ['C', 'Unknown']:
            improvements.append('Overall sustainability optimization')
        
        if len(usage_data) < 5:
            improvements.append('Consistent data tracking')
        
        return improvements
    
    def _intelligent_fallback(self, original_input):
        """Intelligent fallback for errors"""
        return f"I'm here to help with environmental questions and EcoAudit app guidance. While I process your question about '{original_input}', here's what I can immediately assist with:\n\n• Environmental education and sustainability tips\n• Utility usage optimization strategies\n• Recycling and waste management guidance\n• App features and navigation help\n• Community comparisons and insights\n• Technical support and troubleshooting\n\nPlease feel free to ask me about any of these topics!"
    
    def _points_response(self):
        """Detailed points and scoring information"""
        if not self.user_context:
            return "To provide detailed points analysis, please log some utility usage data first. I can then give you comprehensive scoring insights and comparisons."
        
        user_points = self.user_context.get('total_points', 0)
        user_class = self.user_context.get('environmental_class', 'Unknown')
        
        response = f"**Your Sustainability Scoring Analysis:**\n\n"
        response += f"**Current Score:** {user_points} points\n"
        response += f"**Environmental Class:** {user_class}\n\n"
        
        # Class-specific insights
        classes = self.app_knowledge['environmental_classes']
        if user_class in classes:
            response += f"**Class {user_class} Description:** {classes[user_class]}\n\n"
        
        # Scoring breakdown
        response += "**How Points Are Earned:**\n"
        scoring = self.app_knowledge['scoring']
        for score_type, description in scoring.items():
            score_name = score_type.replace('_', ' ').title()
            response += f"• {score_name}: {description}\n"
        
        response += "\n**Improvement Tips:**\n"
        if user_class == 'C':
            response += "• Focus on consistent utility monitoring\n"
            response += "• Implement basic conservation strategies\n"
            response += "• Track progress regularly\n"
        elif user_class == 'B':
            response += "• Optimize peak usage patterns\n"
            response += "• Explore advanced conservation techniques\n"
            response += "• Aim for efficiency bonuses\n"
        else:
            response += "• Maintain excellent practices\n"
            response += "• Share knowledge with community\n"
            response += "• Explore cutting-edge sustainability\n"
        
        return response
    
    def _global_community_response(self):
        """Global community insights and statistics"""
        if not self.global_insights:
            return "I'm gathering comprehensive community data. Please check back shortly for detailed global sustainability insights and trends."
        
        total_users = self.global_insights.get('total_users', 0)
        avg_points = self.global_insights.get('average_points', 0)
        class_dist = self.global_insights.get('class_distribution', {})
        
        response = f"**Global Sustainability Community:**\n\n"
        response += f"**Community Size:** {total_users} active sustainability champions worldwide\n"
        response += f"**Average Performance:** {avg_points:.1f} sustainability points\n\n"
        
        response += "**Environmental Class Distribution:**\n"
        for env_class, count in class_dist.items():
            percentage = (count / total_users) * 100 if total_users > 0 else 0
            class_desc = self.app_knowledge['environmental_classes'].get(env_class, 'Unknown')
            response += f"• **Class {env_class}:** {count} users ({percentage:.1f}%) - {class_desc}\n"
        
        response += "\n**Community Trends:**\n"
        response += "• Growing focus on comprehensive utility optimization\n"
        response += "• Increased engagement with recycling verification\n"
        response += "• Rising interest in AI-powered sustainability insights\n"
        response += "• Strong community collaboration and knowledge sharing\n\n"
        
        response += "**Join the Movement:**\n"
        response += "Become part of our global sustainability community by tracking your impact, sharing insights, and learning from top performers!"
        
        return response
    
    def _recommendations_response(self):
        """AI-powered personalized recommendations"""
        response = "**Personalized Sustainability Recommendations:**\n\n"
        
        if self.user_context:
            user_class = self.user_context.get('environmental_class', 'Unknown')
            
            if user_class == 'A':
                response += "**Maintaining Excellence (Class A):**\n"
                response += "• Continue your outstanding practices\n"
                response += "• Explore cutting-edge sustainability technologies\n"
                response += "• Share your expertise with the community\n"
                response += "• Consider renewable energy investments\n"
                response += "• Lead by example in your local community\n\n"
            
            elif user_class == 'B':
                response += "**Advancing to Excellence (Class B → A):**\n"
                response += "• Implement advanced energy management\n"
                response += "• Optimize peak usage patterns\n"
                response += "• Focus on efficiency bonuses\n"
                response += "• Explore smart home technologies\n"
                response += "• Consistent daily monitoring\n\n"
            
            elif user_class == 'C':
                response += "**Building Strong Foundation (Class C → B):**\n"
                response += "• Start with water conservation basics\n"
                response += "• Implement simple energy-saving practices\n"
                response += "• Focus on consistent tracking\n"
                response += "• Learn from community best practices\n"
                response += "• Set achievable weekly goals\n\n"
        
        response += "**Universal Best Practices:**\n"
        response += "• **Energy:** LED lighting, smart thermostats, efficient appliances\n"
        response += "• **Water:** Low-flow fixtures, leak detection, conservation habits\n"
        response += "• **Gas:** Proper insulation, maintenance, zone heating\n"
        response += "• **Waste:** Reduce, reuse, recycle, verify activities\n"
        response += "• **Tracking:** Regular monitoring, goal setting, progress review\n\n"
        
        response += "**Next Steps:**\n"
        response += "1. Track your current usage patterns\n"
        response += "2. Implement one new conservation strategy\n"
        response += "3. Monitor improvements over time\n"
        response += "4. Engage with community insights\n"
        response += "5. Celebrate progress and set new goals\n"
        
        return response
    
    def _data_analysis_response(self):
        """Data analysis and insights information"""
        response = "**AI Data Analysis & Insights:**\n\n"
        
        response += "**Available Analytics:**\n"
        response += "• **Usage Patterns:** Identify trends in your consumption\n"
        response += "• **Efficiency Scoring:** AI-calculated performance metrics\n"
        response += "• **Predictive Modeling:** Forecast future usage patterns\n"
        response += "• **Anomaly Detection:** Identify unusual consumption spikes\n"
        response += "• **Comparative Analysis:** Benchmark against community averages\n"
        response += "• **Seasonal Adjustments:** Account for weather and seasonal factors\n\n"
        
        response += "**Machine Learning Features:**\n"
        response += "• Random Forest models for usage prediction\n"
        response += "• Clustering algorithms for pattern recognition\n"
        response += "• Regression analysis for efficiency optimization\n"
        response += "• Classification systems for environmental ranking\n\n"
        
        response += "**Data Requirements:**\n"
        response += "• Minimum 3 usage entries for basic analysis\n"
        response += "• 10+ entries for comprehensive insights\n"
        response += "• Regular tracking for trend analysis\n"
        response += "• Household context for accurate benchmarking\n\n"
        
        response += "**Insights You'll Receive:**\n"
        response += "• Personalized efficiency recommendations\n"
        response += "• Usage optimization strategies\n"
        response += "• Performance trend analysis\n"
        response += "• Community comparison metrics\n"
        response += "• Environmental impact projections\n\n"
        
        response += "Start tracking your usage today to unlock powerful AI insights!"
        
        return response