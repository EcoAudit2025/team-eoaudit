"""
Intelligent chatbot for EcoAudit app with ChatGPT-like responses
Provides comprehensive environmental knowledge and smart responses
"""

import re
import random
from datetime import datetime
from difflib import SequenceMatcher
import database as db
try:
    from fuzzywuzzy import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
try:
    import textdistance
    TEXTDIST_AVAILABLE = True
except ImportError:
    TEXTDIST_AVAILABLE = False

class IntelligentEcoBot:
    def __init__(self):
        self.conversation_state = "greeting"
        self.user_name = None
        self.context = {}
        
        # Spell correction dictionary for common typos
        self.spell_corrections = {
            # Common typos and misspellings
            "recicle": "recycle", "recyling": "recycling", "matrial": "material",
            "utilty": "utility", "usege": "usage", "trackr": "tracker",
            "ecoaudt": "ecoaudit", "enviroment": "environment", "sustanability": "sustainability",
            "carbn": "carbon", "footrint": "footprint", "eneregy": "energy",
            "electricty": "electricity", "watter": "water", "gass": "gas",
            "acont": "account", "loginn": "login", "singup": "signup",
            "pasword": "password", "profil": "profile", "histroy": "history",
            "globel": "global", "moniter": "monitor", "analisys": "analysis",
            "recomendation": "recommendation", "conservaton": "conservation",
            "reuuse": "reuse", "reduse": "reduce", "sustnable": "sustainable",
            "enviornment": "environment", "clmate": "climate", "changeing": "changing",
            "renewble": "renewable", "cleaan": "clean", "greeen": "green",
            "efficent": "efficient", "saaving": "saving", "reduceing": "reducing",
            "improveing": "improving", "helpfull": "helpful", "usefull": "useful",
            "compareing": "comparing", "rankig": "ranking", "competng": "competing",
            "chalenges": "challenges", "solutons": "solutions", "probelm": "problem",
            "isue": "issue", "troble": "trouble", "difcult": "difficult",
            "shw": "show", "tel": "tell", "explan": "explain", "halp": "help",
            "hw": "how", "wat": "what", "wen": "when", "wer": "where", "wy": "why",
            "cn": "can", "cud": "could", "shud": "should", "wud": "would",
            "nd": "and", "or": "or", "bt": "but", "thn": "then", "nw": "now",
            "gt": "get", "giv": "give", "tak": "take", "mak": "make", "com": "come",
            "go": "go", "se": "see", "knw": "know", "thnk": "think", "fel": "feel",
            "luk": "look", "wrk": "work", "liv": "live", "sav": "save"
        }
        
        # Intent keywords with variations and common errors
        self.intent_keywords = {
            "greeting": ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", 
                        "helo", "hii", "hy", "gud", "morning", "afternoon", "evening"],
            
            "utility": ["utility", "usage", "tracker", "water", "electricity", "gas", "electric", 
                       "bill", "consumption", "utilty", "usege", "trackr", "watter", "electricty", 
                       "gass", "bil", "consumptin", "utlty", "usag", "trakr"],
            
            "recycling": ["recycle", "recycling", "material", "reuse", "waste", "trash", "disposal",
                         "recicle", "recyling", "matrial", "reuuse", "wast", "trsh", "disposl",
                         "recicling", "matreal", "reuing", "waist", "trassh"],
            
            "energy": ["energy", "save", "reduce", "efficient", "conservation", "power", "saving",
                      "eneregy", "sav", "reduse", "efficent", "conservaton", "powr", "saaving",
                      "enrgy", "savng", "reduceing", "eficent", "conservatn"],
            
            "environment": ["environment", "climate", "carbon", "footprint", "emissions", "greenhouse",
                           "sustainability", "eco", "green", "enviroment", "clmate", "carbn",
                           "footrint", "emisssions", "sustanability", "ecoo", "greeen",
                           "enviornment", "climte", "carbonn", "footpint"],
            
            "account": ["account", "login", "signup", "profile", "register", "create", "password",
                       "acont", "loginn", "singup", "profil", "regster", "creat", "pasword",
                       "acount", "loging", "signp", "proile", "registr", "crete"],
            
            "help": ["help", "assist", "support", "guide", "explain", "show", "tell", "how",
                    "halp", "asist", "suport", "guid", "explan", "shw", "tel", "hw",
                    "hep", "asst", "suprt", "gide", "explian", "sho", "tll"],
            
            "comparison": ["compare", "global", "monitor", "ranking", "leaderboard", "community",
                          "compareing", "globel", "moniter", "rankig", "lederboard", "comunity",
                          "compar", "gobal", "monitr", "rankin", "leadrbord", "cominity"],
            
            "carbon": ["carbon", "footprint", "emissions", "climate", "impact", "greenhouse",
                      "carbn", "footrint", "emisssions", "clmate", "impct", "grenhouse",
                      "carbonn", "footpint", "emisions", "climte", "imact"],
            
            "water": ["water", "conservation", "save water", "leak", "drought", "flow",
                     "watter", "conservaton", "sav watter", "lekk", "drout", "flo",
                     "watr", "conservatn", "save watr", "leak", "drght"],
            
            "problem": ["problem", "error", "issue", "trouble", "not working", "broken", "fix",
                       "probelm", "eror", "isue", "troble", "nt wrking", "brokn", "fx",
                       "problm", "errr", "isu", "truble", "notworking", "brkn"]
        }
        
        # Environmental knowledge base
        self.environmental_facts = {
            "energy": {
                "tips": [
                    "LED bulbs use 75% less energy than incandescent bulbs and last 25 times longer",
                    "Unplugging electronics when not in use can save 5-10% on your electricity bill",
                    "Setting your thermostat 7-10°F lower for 8 hours a day can save 10% annually",
                    "Energy Star appliances use 10-50% less energy than standard models"
                ],
                "facts": [
                    "Buildings consume 40% of global energy and produce 36% of CO2 emissions",
                    "The average home uses 877 kWh per month, varying by climate and size",
                    "Heating and cooling account for about 48% of home energy use"
                ]
            },
            "water": {
                "tips": [
                    "Fix leaks immediately - a single dripping faucet can waste 3,000 gallons annually",
                    "Low-flow showerheads can reduce water usage by 40% without sacrificing pressure",
                    "Running dishwashers and washing machines with full loads saves significant water",
                    "Rain gardens and drought-resistant plants reduce outdoor water needs by 50%"
                ],
                "facts": [
                    "The average American uses 80-100 gallons of water daily",
                    "A 5-minute shower uses 10-25 gallons depending on your showerhead",
                    "Toilets account for 30% of household water consumption"
                ]
            },
            "recycling": {
                "tips": [
                    "Clean containers before recycling to prevent contamination of entire batches",
                    "Remove caps from bottles unless your facility specifically accepts them attached",
                    "Electronics contain valuable metals and should never go in regular trash",
                    "Composting food waste reduces methane emissions from landfills by 50%"
                ],
                "facts": [
                    "Recycling one aluminum can saves enough energy to power a TV for 3 hours",
                    "Americans generate 4.9 pounds of waste per person daily",
                    "Only 32% of waste is currently recycled or composted in the US"
                ]
            },
            "climate": {
                "tips": [
                    "Transportation accounts for 29% of US emissions - consider carpooling or public transit",
                    "Plant-based meals 1-2 times per week can reduce your carbon footprint significantly",
                    "Buying local, seasonal produce reduces transportation emissions",
                    "Proper home insulation can reduce heating/cooling costs by 15%"
                ],
                "facts": [
                    "Global CO2 levels have increased 40% since pre-industrial times",
                    "The average American generates 16 metric tons of CO2 annually",
                    "Forests absorb 2.6 billion tons of CO2 annually - about 1/3 of fossil fuel emissions"
                ]
            }
        }
        
        # Smart response templates
        self.response_templates = {
            "explanation": "Here's what you need to know: {content}. This is important because {reason}.",
            "tips": "Great question! Here are some proven strategies: {tips}. Many users find that {additional_info}.",
            "comparison": "To put this in perspective: {comparison}. For your situation, I'd recommend {recommendation}.",
            "step_by_step": "Let me walk you through this: {steps}. The key is to {emphasis}."
        }

    def get_response(self, user_input):
        """Generate intelligent responses based on user input with error tolerance"""
        if not user_input:
            return "I'm here to help! What would you like to know about sustainability, EcoAudit features, or environmental topics?"
        
        # Clean and normalize input
        cleaned_input = self._clean_and_correct_input(user_input.lower().strip())
        
        # Analyze input for intent and entities with fuzzy matching
        intent = self._analyze_intent_fuzzy(cleaned_input)
        entities = self._extract_entities(cleaned_input)
        
        # Generate contextual response
        if intent == "greeting":
            return self._greeting_response(cleaned_input)
        elif intent == "utility_help":
            return self._utility_guidance(entities)
        elif intent == "recycling_help":
            return self._recycling_guidance(entities)
        elif intent == "environmental_question":
            return self._environmental_knowledge(cleaned_input, entities)
        elif intent == "app_navigation":
            return self._navigation_help(entities)
        elif intent == "carbon_footprint":
            return self._carbon_footprint_info(entities)
        elif intent == "energy_saving":
            return self._energy_saving_advice(entities)
        elif intent == "water_conservation":
            return self._water_conservation_advice(entities)
        elif intent == "comparison":
            return self._comparison_help(entities)
        elif intent == "troubleshooting":
            return self._troubleshooting_help(cleaned_input)
        else:
            return self._intelligent_fallback_with_correction(user_input, cleaned_input)

    def _analyze_intent(self, text):
        """Analyze user intent from input text"""
        # Greeting patterns
        if re.search(r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b', text):
            return "greeting"
        
        # Utility-related questions
        if re.search(r'\b(utility|usage|tracker|water|electricity|gas|electric|bill|consumption)\b', text):
            return "utility_help"
        
        # Recycling questions
        if re.search(r'\b(recycle|recycling|material|reuse|waste|trash|disposal)\b', text):
            return "recycling_help"
        
        # Environmental knowledge
        if re.search(r'\b(environment|climate|carbon|footprint|emissions|greenhouse|sustainability|eco)\b', text):
            return "environmental_question"
        
        # App navigation
        if re.search(r'\b(how to|navigate|find|use|create account|login|sign up)\b', text):
            return "app_navigation"
        
        # Carbon footprint specific
        if re.search(r'\b(carbon footprint|emissions|climate impact|environmental impact)\b', text):
            return "carbon_footprint"
        
        # Energy saving
        if re.search(r'\b(energy|save|reduce|efficient|conservation|power)\b', text):
            return "energy_saving"
        
        # Water conservation
        if re.search(r'\b(water|conservation|save water|leak|drought)\b', text):
            return "water_conservation"
        
        # Comparison questions
        if re.search(r'\b(compare|others|global|community|ranking|leaderboard)\b', text):
            return "comparison"
        
        # Troubleshooting
        if re.search(r'\b(problem|error|issue|not working|broken|help|trouble)\b', text):
            return "troubleshooting"
        
        return "general_question"

    def _extract_entities(self, text):
        """Extract relevant entities from user input"""
        entities = {
            "utilities": [],
            "materials": [],
            "numbers": [],
            "locations": [],
            "time_period": None
        }
        
        # Extract utilities
        utilities = re.findall(r'\b(water|electricity|electric|gas|heating|cooling|energy)\b', text)
        entities["utilities"] = list(set(utilities))
        
        # Extract materials
        materials = re.findall(r'\b(plastic|glass|metal|paper|cardboard|aluminum|battery|electronic)\b', text)
        entities["materials"] = list(set(materials))
        
        # Extract numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        entities["numbers"] = [float(n) for n in numbers]
        
        # Extract time periods
        if re.search(r'\b(daily|monthly|yearly|weekly|annual)\b', text):
            entities["time_period"] = re.search(r'\b(daily|monthly|yearly|weekly|annual)\b', text).group(1)
        
        return entities

    def _clean_and_correct_input(self, text):
        """Clean input text and correct common spelling errors"""
        # Remove extra spaces and normalize
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into words and correct spelling
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Remove punctuation for correction
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            # Check if word needs correction
            if clean_word in self.spell_corrections:
                corrected_words.append(self.spell_corrections[clean_word])
            else:
                # Use fuzzy matching for unknown words
                corrected_word = self._fuzzy_spell_correct(clean_word)
                corrected_words.append(corrected_word)
        
        return ' '.join(corrected_words)

    def _fuzzy_spell_correct(self, word):
        """Use fuzzy matching to correct spelling errors"""
        if len(word) <= 2:
            return word
            
        # Get all known words from spell corrections and intent keywords
        known_words = set()
        known_words.update(self.spell_corrections.values())
        
        for category in self.intent_keywords.values():
            known_words.update(category)
        
        # Add common environmental terms
        known_words.update([
            "sustainable", "environment", "climate", "carbon", "energy", "water", 
            "electricity", "recycling", "conservation", "efficiency", "renewable",
            "footprint", "emissions", "greenhouse", "biodegradable", "pollution"
        ])
        
        # Find best match using fuzzy string matching
        if FUZZY_AVAILABLE:
            try:
                best_match = process.extractOne(word, known_words, scorer=fuzz.ratio)
                if best_match and best_match[1] > 70:  # 70% similarity threshold
                    return best_match[0]
            except:
                pass
        
        # Fallback to basic similarity matching
        best_similarity = 0
        best_word = word
        
        for known_word in known_words:
            if abs(len(word) - len(known_word)) <= 2:  # Length difference threshold
                similarity = self._calculate_similarity(word, known_word)
                if similarity > best_similarity and similarity > 0.7:
                    best_similarity = similarity
                    best_word = known_word
        
        return best_word

    def _calculate_similarity(self, a, b):
        """Calculate similarity between two strings"""
        if TEXTDIST_AVAILABLE:
            try:
                return 1 - (textdistance.levenshtein.normalized_distance(a, b))
            except:
                pass
        
        # Fallback to difflib
        return SequenceMatcher(None, a, b).ratio()

    def _analyze_intent_fuzzy(self, text):
        """Analyze user intent with fuzzy matching for errors"""
        # First try exact pattern matching
        intent = self._analyze_intent(text)
        if intent != "general_question":
            return intent
        
        # Use fuzzy matching for intent detection
        intent_scores = {}
        
        for intent_name, keywords in self.intent_keywords.items():
            score = 0
            for keyword in keywords:
                if FUZZY_AVAILABLE:
                    try:
                        # Check if any word in text fuzzy matches the keyword
                        for word in text.split():
                            ratio = fuzz.partial_ratio(word, keyword)
                            if ratio > 70:  # Threshold for fuzzy match
                                score += ratio / 100
                    except:
                        # Fallback to substring matching
                        if keyword in text or any(self._calculate_similarity(word, keyword) > 0.7 for word in text.split()):
                            score += 1
                else:
                    # Fallback to substring and similarity matching
                    if keyword in text:
                        score += 1
                    else:
                        for word in text.split():
                            if self._calculate_similarity(word, keyword) > 0.7:
                                score += 0.8
            
            intent_scores[intent_name] = score
        
        # Map intent categories to response types
        intent_mapping = {
            "greeting": "greeting",
            "utility": "utility_help", 
            "recycling": "recycling_help",
            "energy": "energy_saving",
            "environment": "environmental_question",
            "account": "app_navigation",
            "help": "app_navigation",
            "comparison": "comparison",
            "carbon": "carbon_footprint",
            "water": "water_conservation",
            "problem": "troubleshooting"
        }
        
        # Find best matching intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0.5:  # Minimum confidence threshold
                return intent_mapping.get(best_intent, "general_question")
        
        return "general_question"

    def _intelligent_fallback_with_correction(self, original_input, cleaned_input):
        """Provide intelligent fallback with spelling correction feedback"""
        # Check if we made significant corrections
        if original_input.lower().strip() != cleaned_input:
            correction_note = f"\n\n*I understood your question as: \"{cleaned_input}\"*\n"
        else:
            correction_note = ""
        
        # Provide context-aware suggestions based on partial matches
        suggestions = []
        
        # Check for partial keyword matches
        input_words = cleaned_input.split()
        
        for word in input_words:
            if any(env_word in word or word in env_word for env_word in ["energy", "save", "power", "electric"]):
                suggestions.append("💡 **Energy Saving Tips**: Ask me about reducing electricity usage or energy-efficient practices")
            elif any(water_word in word or word in water_word for water_word in ["water", "conservation", "leak"]):
                suggestions.append("💧 **Water Conservation**: I can help with water-saving strategies and usage tracking")
            elif any(rec_word in word or word in rec_word for rec_word in ["recycle", "material", "waste", "reuse"]):
                suggestions.append("♻️ **Recycling Guide**: Ask about specific materials or recycling best practices")
            elif any(acc_word in word or word in acc_word for acc_word in ["account", "login", "profile", "sign"]):
                suggestions.append("👤 **Account Help**: I can guide you through creating accounts or logging in")
            elif any(comp_word in word or word in comp_word for comp_word in ["compare", "global", "rank", "leader"]):
                suggestions.append("🌍 **Global Comparison**: Learn about community rankings and environmental performance")
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        for s in suggestions:
            if s not in unique_suggestions:
                unique_suggestions.append(s)
        
        if unique_suggestions:
            response = "I want to help you with that!" + correction_note + "\n\nBased on your question, here are some areas I can assist with:\n\n" + "\n\n".join(unique_suggestions[:3])
            response += "\n\n**You can ask me anything about:**\n• Environmental best practices and sustainability\n• EcoAudit features and how to use them\n• Energy and water conservation tips\n• Recycling and waste reduction\n• Carbon footprint and climate impact"
        else:
            response = "I'd love to help you!" + correction_note + "\n\n**I'm here to assist with:**\n\n🌱 **Environmental Topics**: Energy conservation, water saving, recycling tips, carbon footprint reduction\n\n🏠 **EcoAudit Features**: Account management, utility tracking, AI insights, global comparisons\n\n📊 **Sustainability Guidance**: Best practices, improvement strategies, community insights\n\n**Try asking questions like:**\n• \"How can I reduce my energy bills?\"\n• \"What's the best way to recycle plastic?\"\n• \"How do I create an account?\"\n• \"Show me energy saving tips\""
        
        return response

    def _greeting_response(self, text):
        """Generate personalized greeting"""
        greetings = [
            "Hello! I'm your intelligent environmental assistant. I can help you understand EcoAudit features, provide sustainability tips, and answer environmental questions.",
            "Hi there! I'm here to help you on your sustainability journey. Whether you need help with the app or want environmental advice, just ask!",
            "Welcome! I'm equipped with comprehensive environmental knowledge and can guide you through EcoAudit's features. What would you like to explore?"
        ]
        
        base_greeting = random.choice(greetings)
        
        # Add contextual suggestions
        suggestions = "\n\nYou can ask me about:\n• Tracking your utility usage effectively\n• Recycling specific materials\n• Reducing your carbon footprint\n• Comparing your impact with others\n• Understanding your environmental classification"
        
        return base_greeting + suggestions

    def _utility_guidance(self, entities):
        """Provide intelligent utility usage guidance"""
        utilities = entities.get("utilities", [])
        
        if "water" in utilities:
            tip = random.choice(self.environmental_facts["water"]["tips"])
            fact = random.choice(self.environmental_facts["water"]["facts"])
            return f"**Water Usage Guidance:**\n\n💧 {tip}\n\n📊 **Did you know?** {fact}\n\n**Using EcoAudit:** Go to 'Utility Usage Tracker' to log your monthly water consumption. The AI will analyze your patterns and provide personalized recommendations for improvement."
        
        elif "electricity" in utilities or "electric" in utilities or "energy" in utilities:
            tip = random.choice(self.environmental_facts["energy"]["tips"])
            fact = random.choice(self.environmental_facts["energy"]["facts"])
            return f"**Electricity Usage Guidance:**\n\n⚡ {tip}\n\n📊 **Did you know?** {fact}\n\n**Using EcoAudit:** Track your kWh usage monthly in the 'Utility Usage Tracker'. Our AI will identify anomalies and suggest efficiency improvements."
        
        else:
            return "**Utility Tracking Made Simple:**\n\n🏠 EcoAudit tracks three main utilities: water (gallons), electricity (kWh), and gas (cubic meters).\n\n📈 **Smart Features:**\n• AI-powered usage analysis\n• Personalized recommendations\n• Environmental impact calculation\n• Comparison with similar households\n\n**Getting Started:** Visit 'Utility Usage Tracker' and enter your monthly consumption. The system will classify your environmental performance and provide improvement strategies."

    def _recycling_guidance(self, entities):
        """Provide intelligent recycling guidance"""
        materials = entities.get("materials", [])
        
        if materials:
            material = materials[0]
            if material == "plastic":
                return "**Plastic Recycling Guide:**\n\n♻️ **Key Points:**\n• Look for recycling numbers 1-7 on containers\n• Clean all containers before recycling\n• Remove caps unless your facility accepts them\n• Plastic bags go to special collection points, not curbside bins\n\n🌍 **Environmental Impact:** Recycling one plastic bottle saves enough energy to power a 60W bulb for 6 hours.\n\n**In EcoAudit:** Use 'Materials Recycling Guide' to get specific tips for any material type."
            
            elif material == "glass":
                return "**Glass Recycling Guide:**\n\n♻️ **Key Points:**\n• Glass can be recycled infinitely without quality loss\n• Remove metal lids and plastic labels\n• Separate by color if required in your area\n• Broken glass should be wrapped safely\n\n🌍 **Environmental Impact:** Recycled glass melts at lower temperatures, saving 30% energy compared to new glass production.\n\n**In EcoAudit:** Search for 'glass' in the Materials Recycling Guide for detailed reuse ideas."
            
            else:
                return f"**{material.title()} Recycling:**\n\n♻️ For specific guidance on {material}, use EcoAudit's 'Materials Recycling Guide'. Simply enter the material name and get AI-powered recycling and reuse recommendations.\n\n🌍 **General Tip:** Proper recycling reduces landfill waste and conserves natural resources. Every material recycled makes a difference!"
        
        else:
            tip = random.choice(self.environmental_facts["recycling"]["tips"])
            fact = random.choice(self.environmental_facts["recycling"]["facts"])
            return f"**Smart Recycling Strategies:**\n\n♻️ {tip}\n\n📊 **Impact:** {fact}\n\n**Using EcoAudit:** Visit 'Materials Recycling Guide' to get specific tips for any material. Our AI analyzes sustainability metrics and provides both recycling and creative reuse suggestions."

    def _environmental_knowledge(self, text, entities):
        """Provide comprehensive environmental knowledge"""
        if "carbon" in text or "footprint" in text:
            return self._carbon_footprint_info(entities)
        elif "climate" in text or "warming" in text:
            fact = random.choice(self.environmental_facts["climate"]["facts"])
            tip = random.choice(self.environmental_facts["climate"]["tips"])
            return f"**Climate Change Information:**\n\n🌍 **Current Situation:** {fact}\n\n💡 **What You Can Do:** {tip}\n\n**Track Your Impact:** Use EcoAudit to monitor your household's environmental performance and see how small changes add up to significant impact over time."
        
        elif "sustainability" in text or "eco" in text:
            return "**Sustainability Fundamentals:**\n\n🌱 **Core Principles:**\n• Reduce consumption where possible\n• Reuse items creatively before discarding\n• Recycle properly to close material loops\n• Refuse unnecessary single-use items\n\n📊 **Measuring Progress:** EcoAudit helps you track your environmental performance across multiple dimensions - utility usage, waste reduction, and carbon footprint.\n\n**Your Journey:** Start by establishing baseline measurements, then work on gradual improvements. Small consistent changes create lasting impact."
        
        else:
            return "**Environmental Awareness:**\n\n🌍 Environmental stewardship involves understanding our impact on natural systems and taking responsible action.\n\n**Key Areas to Focus On:**\n• Energy efficiency in daily activities\n• Water conservation practices\n• Waste reduction and proper recycling\n• Sustainable transportation choices\n• Supporting renewable energy when possible\n\n**EcoAudit Support:** Our platform helps you measure, understand, and improve your environmental impact through data-driven insights and community comparison."

    def _navigation_help(self, entities):
        """Provide intelligent app navigation help"""
        return "**EcoAudit Navigation Guide:**\n\n🏠 **Main Features:**\n• **User Profile:** Create accounts (public for community comparison or private for personal tracking)\n• **Utility Usage Tracker:** Log monthly water, electricity, and gas consumption\n• **Materials Recycling Guide:** Get AI-powered recycling and reuse tips\n• **AI Insights Dashboard:** View personalized analytics and predictions\n• **My History:** Track your progress over time\n• **Global Monitor:** Compare with community members worldwide\n\n💡 **Getting Started:**\n1. Create an account in 'User Profile'\n2. Log your first utility usage in 'Utility Usage Tracker'\n3. Explore materials recycling for specific items\n4. Check AI insights after a few data entries\n\n**Pro Tip:** Public accounts contribute to community data and can earn ranking positions, while private accounts focus on personal improvement."

    def _carbon_footprint_info(self, entities):
        """Provide carbon footprint information"""
        return "**Understanding Your Carbon Footprint:**\n\n🌍 **Definition:** Your carbon footprint measures the total greenhouse gas emissions caused by your activities, measured in CO2 equivalent.\n\n📊 **Average Impact:**\n• US average: 16 metric tons CO2/year per person\n• Global average: 4 metric tons CO2/year per person\n• Paris Agreement target: 2.3 metric tons CO2/year per person\n\n🏠 **Household Breakdown:**\n• Heating/Cooling: 42% of emissions\n• Transportation: 29%\n• Electricity: 28%\n• Water heating: 18%\n\n**EcoAudit Calculation:** We estimate your footprint based on utility usage, household size, and location. Track monthly to see improvement trends and compare with similar households globally."

    def _energy_saving_advice(self, entities):
        """Provide energy saving advice"""
        tip = random.choice(self.environmental_facts["energy"]["tips"])
        return f"**Energy Efficiency Strategies:**\n\n⚡ **Immediate Action:** {tip}\n\n🏠 **Comprehensive Approach:**\n• Upgrade to LED lighting (saves $75/year for average home)\n• Use programmable thermostats (10% annual savings)\n• Seal air leaks around windows and doors\n• Unplug electronics when not in use\n• Choose Energy Star appliances for replacements\n\n📊 **Track Progress:** Monitor your kWh usage monthly in EcoAudit's Utility Tracker. The AI will identify patterns and suggest personalized efficiency improvements based on your specific usage patterns."

    def _water_conservation_advice(self, entities):
        """Provide water conservation advice"""
        tip = random.choice(self.environmental_facts["water"]["tips"])
        return f"**Water Conservation Strategies:**\n\n💧 **Priority Action:** {tip}\n\n🚿 **Daily Habits:**\n• Take shorter showers (save 25 gallons per 5-minute reduction)\n• Fix leaks immediately (saves 3,000+ gallons annually)\n• Run full loads in dishwashers and washing machines\n• Install low-flow fixtures\n• Collect rainwater for garden use\n\n📊 **Track Impact:** Log your monthly water usage in EcoAudit to identify trends and compare with efficient households in your climate zone."

    def _comparison_help(self, entities):
        """Provide comparison and ranking information"""
        return "**Community Comparison Features:**\n\n🏆 **Global Monitor:** Compare your environmental performance with users worldwide who have made their data public.\n\n📊 **Ranking System:**\n• **Class A (Excellent):** Top-tier environmental performance\n• **Class B (Good):** Above-average sustainability practices\n• **Class C (Developing):** Opportunities for improvement identified\n\n🌍 **What You'll See:**\n• Environmental champions in each category\n• Usage patterns by location type (urban/suburban/rural)\n• Community averages for comparison\n• Best practices from top performers\n\n**Privacy Note:** Only public account data appears in global comparisons. Private accounts can still see community averages without sharing personal data."

    def _troubleshooting_help(self, text):
        """Provide troubleshooting help"""
        if "login" in text or "account" in text:
            return "**Login Troubleshooting:**\n\n🔐 **Common Solutions:**\n• Ensure you're selecting the correct account type (public/private)\n• Username is case-sensitive\n• Try creating an account if you haven't already\n• Each username can have both a public and private account\n\n**Account Types:**\n• **Private:** Personal tracking only\n• **Public:** Contributes to community data and rankings\n\n**Still having issues?** Try creating a new account - the process takes less than a minute."
        
        elif "data" in text or "tracking" in text:
            return "**Data Tracking Issues:**\n\n📊 **Usage Limits:**\n• 2 utility entries per day per user\n• Limits reset at midnight\n• Unlimited material searches\n\n**Data Requirements:**\n• Water: gallons per month\n• Electricity: kWh per month\n• Gas: cubic meters per month\n\n**Tips:** Use your utility bills for accurate measurements. Estimates are acceptable for getting started."
        
        else:
            return "**General Troubleshooting:**\n\n🔧 **Common Solutions:**\n• Refresh the page if features aren't loading\n• Check your internet connection\n• Try logging out and back in\n• Clear browser cache if experiencing persistent issues\n\n**Feature-Specific Help:**\n• Ask about specific features you're having trouble with\n• Most issues resolve with a page refresh\n• Data saves automatically when entered correctly\n\n**Need More Help?** Be specific about what's not working, and I can provide targeted assistance."

    def _intelligent_fallback(self, text):
        """Provide intelligent fallback responses"""
        # Analyze what the user might be looking for
        if len(text.split()) == 1:
            return f"I'd love to help you with '{text}'! Could you provide a bit more context? For example:\n• Are you looking for information about {text}?\n• Do you need help using a specific feature?\n• Would you like environmental tips related to {text}?\n\nJust let me know what specific aspect interests you most."
        
        elif "?" in text:
            return "That's a great question! While I might not have covered that specific topic, I can help you with:\n\n🌍 **Environmental Topics:** Energy saving, water conservation, recycling, carbon footprint\n🏠 **EcoAudit Features:** Account creation, utility tracking, AI insights, global comparisons\n📊 **Sustainability:** Tips for reducing environmental impact and understanding your data\n\nCould you rephrase your question or let me know which area interests you most?"
        
        else:
            return "I want to give you the most helpful response possible! Based on what you've shared, I can provide information about:\n\n• **Environmental best practices** for sustainability\n• **EcoAudit features** for tracking your impact\n• **Specific guidance** for utility usage or recycling\n• **Community insights** from global data\n\nWhat specific aspect would be most valuable for you right now?"