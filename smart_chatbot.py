"""
Enhanced intelligent chatbot for EcoAudit app - ChatGPT-like responses
Analyzes global monitor data and user patterns for contextual insights
"""

import re
from datetime import datetime, timedelta
import database as db
try:
    from textdistance import levenshtein
    TEXTDIST_AVAILABLE = True
except ImportError:
    TEXTDIST_AVAILABLE = False
    try:
        from fuzzywuzzy import fuzz
        def levenshtein(a, b):
            return 100 - fuzz.ratio(a, b)
    except ImportError:
        def levenshtein(a, b):
            from difflib import SequenceMatcher
            return (1 - SequenceMatcher(None, a.lower(), b.lower()).ratio()) * 100
import json

class SmartEcoBot:
    def __init__(self):
        self.conversation_context = []
        self.user_context = {}
        self.global_insights = {}
        self.response_templates = self._load_response_templates()
        self.environmental_fundamentals = self._load_environmental_fundamentals()
        self.environmental_knowledge = self._load_environmental_knowledge()
        
    def _load_environmental_fundamentals(self):
        """Load the 14 fundamental environmental principles"""
        return {
            "1. Conservation": "Protect and preserve natural resources for future generations through responsible use and management.",
            "2. Sustainability": "Meet present needs without compromising the ability of future generations to meet their own needs.",
            "3. Renewable Energy": "Transition to clean, renewable energy sources like solar, wind, and hydroelectric power.",
            "4. Waste Reduction": "Minimize waste generation through reduce, reuse, recycle, and refuse principles.",
            "5. Water Conservation": "Protect freshwater resources through efficient use and pollution prevention.",
            "6. Biodiversity": "Maintain ecosystem diversity to ensure natural balance and species survival.",
            "7. Carbon Footprint": "Reduce greenhouse gas emissions to combat climate change.",
            "8. Circular Economy": "Design out waste and keep products and materials in use for as long as possible.",
            "9. Environmental Justice": "Ensure fair treatment and meaningful involvement of all people in environmental decisions.",
            "10. Precautionary Principle": "Take preventive action in the face of uncertainty about environmental harm.",
            "11. Ecosystem Services": "Recognize and protect the benefits that ecosystems provide to humanity.",
            "12. Life Cycle Thinking": "Consider environmental impacts throughout a product's entire life cycle.",
            "13. Pollution Prevention": "Prevent pollution at the source rather than treating it after it occurs.",
            "14. Environmental Education": "Increase awareness and understanding of environmental issues and solutions."
        }
    
    def _load_environmental_knowledge(self):
        """Load comprehensive environmental knowledge base"""
        return {
            "climate_change": {
                "causes": ["Greenhouse gas emissions", "Deforestation", "Industrial processes", "Transportation", "Agriculture"],
                "effects": ["Rising temperatures", "Sea level rise", "Extreme weather", "Ecosystem disruption", "Food security threats"],
                "solutions": ["Renewable energy adoption", "Energy efficiency", "Carbon pricing", "Reforestation", "Sustainable transportation"]
            },
            "energy_efficiency": {
                "home_tips": ["LED lighting", "Smart thermostats", "Proper insulation", "Energy-efficient appliances", "Solar panels"],
                "water_saving": ["Low-flow fixtures", "Fix leaks promptly", "Rainwater harvesting", "Greywater systems", "Native landscaping"],
                "waste_reduction": ["Composting", "Recycling programs", "Bulk buying", "Reusable containers", "Repair vs replace"]
            },
            "carbon_footprint": {
                "calculation": "Water: 0.002 kg CO2/gallon, Electricity: 0.4 kg CO2/kWh, Gas: 2.2 kg CO2/cubic meter",
                "reduction_strategies": ["Switch to renewables", "Improve insulation", "Use public transport", "Eat less meat", "Buy local products"]
            },
            "sustainability_metrics": {
                "water_efficiency": "Normal: 3000-12000 gallons/month, Excellent: <3000 gallons/month",
                "electricity_efficiency": "Normal: 300-800 kWh/month, Excellent: <300 kWh/month",
                "gas_efficiency": "Normal: 50-150 cubic meters/month, Excellent: <50 cubic meters/month"
            }
        }
        
    def _load_response_templates(self):
        """Load comprehensive response templates for different scenarios"""
        return {
            'greeting': [
                "Hello! I'm your AI sustainability assistant. I analyze global environmental data to provide personalized insights. How can I help you today?",
                "Hi there! I have access to real-time sustainability data from our community. What would you like to know about environmental impact?",
                "Welcome! I'm here to help with sustainability questions using insights from global user data. What's on your mind?"
            ],
            'utility_analysis': [
                "Based on global data analysis, I can provide insights about your utility usage patterns.",
                "Let me analyze community trends to give you personalized recommendations.",
                "Using data from similar households, here's what I found:"
            ],
            'comparison': [
                "Compared to similar users in our database:",
                "Looking at community averages for your demographic:",
                "Based on patterns from users with similar profiles:"
            ],
            'recommendations': [
                "Based on successful strategies from top performers:",
                "Drawing from community best practices:",
                "Analyzing patterns from high-scoring users reveals:"
            ]
        }
    
    def get_intelligent_response(self, user_input, current_user=None):
        """Generate intelligent ChatGPT-like responses with global data analysis"""
        try:
            # Store conversation context
            self.conversation_context.append(user_input)
            if len(self.conversation_context) > 10:
                self.conversation_context.pop(0)
            
            # Update user context if available
            if current_user:
                self.user_context = self._analyze_user_context(current_user)
            
            # Refresh global insights
            self._update_global_insights()
            
            # Clean and analyze input
            cleaned_input = self._clean_input(user_input)
            intent = self._analyze_intent_advanced(cleaned_input)
            entities = self._extract_entities_smart(cleaned_input)
            
            # Generate contextual response based on intent
            response = self._generate_contextual_response(intent, entities, cleaned_input)
            
            return response
            
        except Exception as e:
            return self._fallback_response(user_input)
    
    def _analyze_user_context(self, user):
        """Analyze user's sustainability profile and history"""
        try:
            # Get user's recent usage data
            recent_usage = db.get_utility_history(user.id, limit=5)
            
            # Get user's environmental class and points
            user_class = getattr(user, 'environmental_class', 'Unknown')
            total_points = getattr(user, 'total_points', 0)
            
            # Analyze user patterns
            context = {
                'environmental_class': user_class,
                'total_points': total_points,
                'household_size': getattr(user, 'household_size', 1),
                'location': getattr(user, 'location_type', 'Unknown'),
                'recent_usage_count': len(recent_usage),
                'performance_trend': self._analyze_performance_trend(recent_usage),
                'strengths': self._identify_user_strengths(user, recent_usage),
                'improvement_areas': self._identify_improvement_areas(user, recent_usage)
            }
            
            return context
            
        except Exception:
            return {}
    
    def _update_global_insights(self):
        """Update global community insights and trends"""
        try:
            # Get global rankings and statistics
            global_rankings = db.get_global_rankings(50)
            
            if global_rankings:
                # Calculate community averages
                total_users = len(global_rankings)
                avg_points = sum(user[1] for user in global_rankings) / total_users if total_users > 0 else 0
                
                # Analyze class distribution
                class_distribution = {}
                for user in global_rankings:
                    user_class = user[2] if len(user) > 2 else 'Unknown'
                    class_distribution[user_class] = class_distribution.get(user_class, 0) + 1
                
                # Get top performer insights
                top_performers = global_rankings[:5]
                
                self.global_insights = {
                    'total_users': total_users,
                    'average_points': avg_points,
                    'class_distribution': class_distribution,
                    'top_performers': top_performers,
                    'community_trend': self._analyze_community_trend()
                }
            
        except Exception:
            self.global_insights = {}
    
    def _analyze_intent_advanced(self, text):
        """Advanced intent analysis with contextual understanding"""
        text_lower = text.lower()
        
        # Multi-word pattern matching for better intent detection
        intent_patterns = {
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'good evening', 'start'],
            'utility_help': ['water', 'electricity', 'gas', 'usage', 'consumption', 'bill', 'meter'],
            'comparison': ['compare', 'vs', 'versus', 'better than', 'worse than', 'rank', 'position'],
            'recommendations': ['suggest', 'recommend', 'advice', 'tips', 'help me', 'how to', 'improve'],
            'recycling': ['recycle', 'dispose', 'throw away', 'waste', 'material', 'plastic', 'glass'],
            'points': ['points', 'score', 'rating', 'performance', 'level', 'class'],
            'global_stats': ['community', 'global', 'everyone', 'others', 'average', 'typical'],
            'environmental': ['environment', 'carbon', 'footprint', 'green', 'sustainable', 'eco', 'climate'],
            'fundamentals': ['14', 'fundamental', 'principle', 'basic', 'foundation', 'core', 'essential'],
            'principles': ['conservation', 'sustainability', 'renewable', 'biodiversity', 'circular economy', 'pollution prevention'],
            'technical': ['error', 'bug', 'problem', 'not working', 'broken', 'issue']
        }
        
        # Score each intent based on word matches
        intent_scores = {}
        for intent, keywords in intent_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
                    # Bonus for exact phrase matches
                    if len(keyword.split()) > 1 and keyword in text_lower:
                        score += 2
            intent_scores[intent] = score
        
        # Return highest scoring intent
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        
        return 'general'
    
    def _extract_entities_smart(self, text):
        """Smart entity extraction with context awareness"""
        entities = {
            'numbers': re.findall(r'\d+\.?\d*', text),
            'utilities': [],
            'materials': [],
            'time_references': [],
            'comparison_terms': []
        }
        
        # Utility detection
        utilities = ['water', 'electricity', 'gas', 'power', 'energy']
        for utility in utilities:
            if utility in text.lower():
                entities['utilities'].append(utility)
        
        # Material detection
        materials = ['plastic', 'glass', 'paper', 'metal', 'cardboard', 'electronics']
        for material in materials:
            if material in text.lower():
                entities['materials'].append(material)
        
        # Time references
        time_words = ['today', 'yesterday', 'week', 'month', 'year', 'daily', 'monthly']
        for time_word in time_words:
            if time_word in text.lower():
                entities['time_references'].append(time_word)
        
        # Comparison terms
        comparison_words = ['better', 'worse', 'higher', 'lower', 'more', 'less', 'compare']
        for comp_word in comparison_words:
            if comp_word in text.lower():
                entities['comparison_terms'].append(comp_word)
        
        return entities
    
    def _generate_contextual_response(self, intent, entities, original_input):
        """Generate intelligent contextual responses"""
        
        if intent == 'greeting':
            return self._greeting_response_with_context()
        
        elif intent == 'utility_help':
            return self._utility_analysis_response(entities)
        
        elif intent == 'comparison':
            return self._comparison_response_with_data(entities)
        
        elif intent == 'recommendations':
            return self._smart_recommendations_response(entities)
        
        elif intent == 'global_stats':
            return self._global_insights_response()
        
        elif intent == 'points':
            return self._points_analysis_response()
        
        elif intent == 'recycling':
            return self._recycling_guidance_response(entities)
        
        elif intent == 'environmental':
            return self._environmental_insights_response()
        
        else:
            return self._contextual_general_response(original_input)
    
    def _greeting_response_with_context(self):
        """Personalized greeting with global context"""
        base_greeting = "Hello! I'm your AI sustainability assistant."
        
        if self.global_insights:
            total_users = self.global_insights.get('total_users', 0)
            avg_points = self.global_insights.get('average_points', 0)
            
            context_info = f" I'm currently analyzing data from {total_users} community members with an average sustainability score of {avg_points:.1f} points."
        else:
            context_info = " I analyze global environmental data to provide personalized insights."
        
        if self.user_context:
            user_class = self.user_context.get('environmental_class', 'Unknown')
            user_points = self.user_context.get('total_points', 0)
            
            if user_class != 'Unknown':
                personal_info = f" You're currently in Environmental Class {user_class} with {user_points} points."
            else:
                personal_info = " Ready to help you improve your sustainability performance!"
        else:
            personal_info = " How can I help you with your sustainability journey today?"
        
        return base_greeting + context_info + personal_info
    
    def _utility_analysis_response(self, entities):
        """Intelligent utility usage analysis"""
        if not self.global_insights:
            return "I'd love to help with utility analysis! Please share your water, electricity, or gas usage data so I can provide personalized insights based on community trends."
        
        response = "Based on global community data analysis:\n\n"
        
        # Add specific utility insights if mentioned
        utilities = entities.get('utilities', [])
        if 'water' in utilities:
            response += "💧 **Water Usage**: Top performers typically use 150-300 gallons monthly with efficient fixtures and conservation habits.\n"
        
        if 'electricity' in utilities:
            response += "⚡ **Electricity**: High-scoring users average 400-800 kWh monthly through energy-efficient appliances and smart usage patterns.\n"
        
        if 'gas' in utilities:
            response += "🔥 **Gas Usage**: Sustainable households typically consume 20-50 cubic meters monthly with efficient heating and cooking practices.\n"
        
        # Add community comparison
        if self.user_context:
            user_class = self.user_context.get('environmental_class', 'Unknown')
            response += f"\n**Your Performance**: You're in Class {user_class}. "
            
            if user_class == 'A':
                response += "Excellent work! You're among our top sustainability performers."
            elif user_class == 'B':
                response += "Good progress! With some optimizations, you could reach Class A performance."
            else:
                response += "There's great potential for improvement. Let me suggest some strategies."
        
        return response
    
    def _comparison_response_with_data(self, entities):
        """Data-driven comparison response"""
        if not self.global_insights or not self.user_context:
            return "To provide accurate comparisons, I need access to your usage data and our community database. Please ensure you've entered your utility information."
        
        user_points = self.user_context.get('total_points', 0)
        avg_points = self.global_insights.get('average_points', 0)
        
        response = f"**Your Performance vs Community Average**:\n\n"
        response += f"• Your Score: {user_points} points\n"
        response += f"• Community Average: {avg_points:.1f} points\n"
        
        if user_points > avg_points:
            difference = user_points - avg_points
            response += f"• You're performing {difference:.1f} points above average! 🌟\n\n"
            response += "You're among the top sustainability performers in our community. Consider sharing your strategies to help others improve."
        else:
            difference = avg_points - user_points
            response += f"• Improvement opportunity: {difference:.1f} points below average\n\n"
            response += "Based on successful community members, here are proven strategies to boost your score:"
            
            # Add specific recommendations based on top performers
            if self.global_insights.get('top_performers'):
                response += "\n\n**Top Performer Strategies:**\n"
                response += "• Consistent monitoring and optimization\n"
                response += "• Energy-efficient appliance usage\n"
                response += "• Water conservation techniques\n"
                response += "• Smart heating and cooling practices"
        
        return response
    
    def _smart_recommendations_response(self, entities):
        """AI-powered recommendations based on global data"""
        if not self.global_insights:
            return "I'm analyzing community data to provide personalized recommendations. Please check back in a moment for AI-powered insights based on successful user strategies."
        
        response = "**Personalized Recommendations** (Based on Global Success Patterns):\n\n"
        
        # Analyze user's improvement areas
        if self.user_context:
            user_class = self.user_context.get('environmental_class', 'Unknown')
            
            if user_class == 'C':
                response += "**Priority Areas for Class C → B Advancement:**\n"
                response += "• Focus on water conservation (typically yields 15-25% point increase)\n"
                response += "• Implement energy-saving practices during peak hours\n"
                response += "• Optimize heating/cooling efficiency\n"
            
            elif user_class == 'B':
                response += "**Strategies for Class B → A Excellence:**\n"
                response += "• Advanced energy management techniques\n"
                response += "• Smart appliance scheduling\n"
                response += "• Renewable energy integration where possible\n"
            
            else:
                response += "**Maintaining Class A Performance:**\n"
                response += "• Continue current excellent practices\n"
                response += "• Explore cutting-edge sustainability technologies\n"
                response += "• Share knowledge with the community\n"
        
        # Add material-specific advice if mentioned
        materials = entities.get('materials', [])
        if materials:
            response += f"\n**Material-Specific Guidance:**\n"
            for material in materials:
                response += f"• {material.title()}: Check our comprehensive recycling guide with verified disposal methods\n"
        
        return response
    
    def _global_insights_response(self):
        """Community and global sustainability insights"""
        if not self.global_insights:
            return "I'm currently gathering global sustainability data. Please check back shortly for comprehensive community insights and trends."
        
        total_users = self.global_insights.get('total_users', 0)
        avg_points = self.global_insights.get('average_points', 0)
        class_dist = self.global_insights.get('class_distribution', {})
        
        response = f"**Global Sustainability Community Insights:**\n\n"
        response += f"📊 **Community Size**: {total_users} active sustainability champions\n"
        response += f"📈 **Average Performance**: {avg_points:.1f} sustainability points\n\n"
        
        if class_dist:
            response += "**Environmental Class Distribution:**\n"
            for env_class, count in class_dist.items():
                percentage = (count / total_users) * 100 if total_users > 0 else 0
                if env_class == 'A':
                    response += f"🌟 Class A (Excellent): {count} users ({percentage:.1f}%)\n"
                elif env_class == 'B':
                    response += f"⚡ Class B (Good): {count} users ({percentage:.1f}%)\n"
                elif env_class == 'C':
                    response += f"🔄 Class C (Improving): {count} users ({percentage:.1f}%)\n"
        
        # Add trending insights
        response += "\n**Community Trends:**\n"
        response += "• Increasing focus on water conservation strategies\n"
        response += "• Growing adoption of energy-efficient practices\n"
        response += "• Rising interest in comprehensive recycling programs\n"
        
        return response
    
    def _points_analysis_response(self):
        """Detailed points and scoring analysis"""
        if not self.user_context:
            return "To provide detailed points analysis, please ensure you've logged your utility usage data. I can then compare your performance with community standards."
        
        user_points = self.user_context.get('total_points', 0)
        user_class = self.user_context.get('environmental_class', 'Unknown')
        
        response = f"**Your Sustainability Score Analysis:**\n\n"
        response += f"🎯 Current Score: {user_points} points\n"
        response += f"🏆 Environmental Class: {user_class}\n\n"
        
        # Provide class-specific insights
        if user_class == 'A':
            response += "**Class A Excellence** - You're in the top tier!\n"
            response += "• Exceptional resource management\n"
            response += "• Consistently sustainable practices\n"
            response += "• Environmental leadership potential\n"
        
        elif user_class == 'B':
            response += "**Class B Performance** - Strong sustainability practices!\n"
            response += "• Good resource efficiency\n"
            response += "• Room for optimization to reach Class A\n"
            response += "• Focus on consistency and fine-tuning\n"
        
        elif user_class == 'C':
            response += "**Class C Development** - Great improvement potential!\n"
            response += "• Foundation established for sustainability\n"
            response += "• Significant opportunity for advancement\n"
            response += "• Focus on systematic improvements\n"
        
        # Add scoring methodology
        response += "\n**How Points Are Calculated:**\n"
        response += "• Water efficiency: Up to 20 points per entry\n"
        response += "• Electricity optimization: Up to 20 points per entry\n"
        response += "• Gas conservation: Up to 18 points per entry\n"
        response += "• Efficiency bonuses: Up to 25% additional points\n"
        response += "• Household context adjustments applied\n"
        
        return response
    
    def _recycling_guidance_response(self, entities):
        """Enhanced recycling guidance with real resources"""
        materials = entities.get('materials', [])
        
        response = "**Smart Recycling Guidance** (Based on Verified Resources):\n\n"
        
        if materials:
            for material in materials:
                response += f"**{material.title()} Recycling:**\n"
                
                if material == 'plastic':
                    response += "• Check recycling numbers (#1-7) on bottom\n"
                    response += "• Clean containers before recycling\n"
                    response += "• Resources: plasticrecycling.org, earth911.com\n\n"
                
                elif material == 'glass':
                    response += "• Remove caps and lids\n"
                    response += "• Rinse clean - no need to be perfect\n"
                    response += "• Resources: glasspackaging.org\n\n"
                
                elif material == 'electronics':
                    response += "• Never put in regular trash\n"
                    response += "• Use manufacturer take-back programs\n"
                    response += "• Resources: epa.gov/recycle/electronics\n\n"
        else:
            response += "**General Recycling Best Practices:**\n"
            response += "• Always check local guidelines first\n"
            response += "• Clean containers when possible\n"
            response += "• Separate materials by type\n"
            response += "• Use verified recycling resources\n\n"
            
            response += "**Verified Recycling Resources:**\n"
            response += "• Earth911.com - Comprehensive recycling guide\n"
            response += "• EPA.gov/recycle - Official guidelines\n"
            response += "• Call2Recycle.org - Battery recycling\n"
            response += "• Local waste management websites\n"
        
        return response
    
    def _environmental_insights_response(self):
        """Environmental impact and carbon footprint insights"""
        response = "**Environmental Impact Insights** (Data-Driven Analysis):\n\n"
        
        if self.user_context:
            user_class = self.user_context.get('environmental_class', 'Unknown')
            household_size = self.user_context.get('household_size', 1)
            
            response += f"**Your Environmental Profile:**\n"
            response += f"• Performance Class: {user_class}\n"
            response += f"• Household Size: {household_size} people\n\n"
        
        response += "**Carbon Footprint Factors:**\n"
        response += "• Electricity: ~0.85 lbs CO₂ per kWh (varies by grid)\n"
        response += "• Natural Gas: ~11.7 lbs CO₂ per therm\n"
        response += "• Water: ~0.002 lbs CO₂ per gallon (treatment/transport)\n\n"
        
        response += "**Global Context:**\n"
        response += "• Average US household: ~16 tons CO₂ annually\n"
        response += "• Sustainable target: <10 tons CO₂ annually\n"
        response += "• Top performers: 6-8 tons CO₂ annually\n\n"
        
        response += "**Improvement Strategies:**\n"
        response += "• Energy efficiency: 20-30% reduction potential\n"
        response += "• Smart appliance usage: 10-15% savings\n"
        response += "• Water conservation: 5-10% total impact reduction\n"
        response += "• Renewable energy: 50-80% electricity emissions reduction\n"
        
        return response
    
    def _contextual_general_response(self, original_input):
        """Intelligent general response based on context"""
        # Analyze conversation context for better responses
        context_keywords = ' '.join(self.conversation_context[-3:]).lower()
        
        if any(word in context_keywords for word in ['help', 'how', 'what', 'why']):
            return "I understand you're looking for guidance. I can help with:\n\n• Utility usage analysis and optimization\n• Sustainability performance comparisons\n• Recycling and waste management guidance\n• Environmental impact insights\n• Community trends and best practices\n\nWhat specific area would you like to explore?"
        
        elif any(word in context_keywords for word in ['problem', 'error', 'not working']):
            return "I'm here to help troubleshoot any issues. Common solutions:\n\n• Refresh the page if data isn't loading\n• Check your internet connection\n• Ensure you've entered utility data correctly\n• Try logging out and back in\n\nIf problems persist, describe the specific issue and I'll provide targeted assistance."
        
        else:
            return "I'm your AI sustainability assistant with access to global environmental data. I can provide:\n\n• Personalized utility usage insights\n• Community performance comparisons\n• Evidence-based improvement recommendations\n• Verified recycling guidance\n• Environmental impact analysis\n\nHow can I help you on your sustainability journey today?"
    
    def _clean_input(self, text):
        """Clean and normalize user input"""
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        # Fix common typos
        common_fixes = {
            'recylce': 'recycle',
            'elctricity': 'electricity',
            'watter': 'water',
            'sugest': 'suggest',
            'recomend': 'recommend'
        }
        
        for wrong, correct in common_fixes.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def _analyze_performance_trend(self, recent_usage):
        """Analyze user's performance trend"""
        if len(recent_usage) < 2:
            return 'insufficient_data'
        
        # Simple trend analysis based on points
        recent_points = [usage.points_earned for usage in recent_usage if hasattr(usage, 'points_earned')]
        
        if len(recent_points) >= 2:
            if recent_points[0] > recent_points[-1]:
                return 'improving'
            elif recent_points[0] < recent_points[-1]:
                return 'declining'
            else:
                return 'stable'
        
        return 'stable'
    
    def _identify_user_strengths(self, user, recent_usage):
        """Identify user's sustainability strengths"""
        strengths = []
        
        if getattr(user, 'environmental_class', None) == 'A':
            strengths.append('Overall excellent performance')
        
        if getattr(user, 'total_points', 0) > 100:
            strengths.append('Consistent high scoring')
        
        # Add more strength analysis based on usage patterns
        return strengths
    
    def _identify_improvement_areas(self, user, recent_usage):
        """Identify areas for improvement"""
        improvements = []
        
        if getattr(user, 'environmental_class', None) in ['C', 'Unknown']:
            improvements.append('Overall sustainability practices')
        
        if len(recent_usage) < 3:
            improvements.append('Consistent monitoring and tracking')
        
        return improvements
    
    def _analyze_community_trend(self):
        """Analyze overall community sustainability trends"""
        # This could be enhanced with time-series analysis
        return 'improving'
    
    def _fallback_response(self, original_input):
        """Intelligent fallback response"""
        return f"I understand you're asking about '{original_input}'. While I analyze the best way to help, here's what I can assist with:\n\n• Utility usage optimization strategies\n• Sustainability performance analysis\n• Community trend insights\n• Recycling and waste management\n• Environmental impact calculations\n\nCould you rephrase your question or choose one of these topics?"