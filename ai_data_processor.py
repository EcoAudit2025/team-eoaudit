import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import database as db
from ai_models import usage_predictor, recommendation_engine, dl_analyzer
import json
import os

class AIDataProcessor:
    """Main AI data processing engine for EcoAudit"""
    
    def __init__(self):
        self.models_trained = False
        self.last_training_time = None
        self.model_performance = {}
        
    def initialize_ai_system(self):
        """Initialize the AI system with existing data"""
        try:
            # Load existing data from database
            historical_data = self._load_historical_data()
            
            if len(historical_data) > 0:
                # Train models with existing data
                self.train_models(historical_data)
                return True, f"AI system initialized with {len(historical_data)} historical records"
            else:
                # Train with synthetic data for bootstrap
                self.train_models([])
                return True, "AI system initialized with baseline models"
                
        except Exception as e:
            return False, f"Failed to initialize AI system: {str(e)}"
    
    def _load_historical_data(self):
        """Load historical data from database"""
        try:
            # Get utility usage history
            utility_data = db.get_utility_history(limit=1000)
            
            # Convert to required format
            processed_data = []
            for record in utility_data:
                processed_data.append({
                    'timestamp': record.timestamp,
                    'water_gallons': record.water_gallons,
                    'electricity_kwh': record.electricity_kwh,
                    'gas_cubic_m': record.gas_cubic_m,
                    'water_status': record.water_status,
                    'electricity_status': record.electricity_status,
                    'gas_status': record.gas_status
                })
            
            return processed_data
            
        except Exception as e:
            print(f"Error loading historical data: {e}")
            return []
    
    def train_models(self, data):
        """Train all AI models"""
        try:
            # Train utility usage predictor
            performance = usage_predictor.train_models(pd.DataFrame(data))
            self.model_performance = performance
            
            # Train deep learning model if enough data
            if len(data) >= 50:
                dl_history = dl_analyzer.train_deep_model(data)
                if dl_history:
                    self.model_performance['dl_loss'] = float(dl_history.history['loss'][-1])
            
            self.models_trained = True
            self.last_training_time = datetime.now()
            
            # Save models
            usage_predictor.save_models()
            
            return True, "Models trained successfully"
            
        except Exception as e:
            return False, f"Model training failed: {str(e)}"
    
    def analyze_new_usage(self, water_gallons, electricity_kwh, gas_cubic_m):
        """Analyze new usage data with AI"""
        try:
            current_data = {
                'timestamp': datetime.now(),
                'water_gallons': water_gallons,
                'electricity_kwh': electricity_kwh,
                'gas_cubic_m': gas_cubic_m
            }
            
            analysis_results = {}
            
            # Get AI predictions
            if self.models_trained:
                predictions = usage_predictor.predict_usage(current_data)
                if predictions:
                    analysis_results['predictions'] = predictions
                    
                    # Anomaly detection
                    if predictions['anomaly_probability'] > 0.7:
                        analysis_results['anomaly_alert'] = {
                            'level': 'high',
                            'message': 'Unusual usage pattern detected - please verify readings',
                            'probability': predictions['anomaly_probability']
                        }
                    elif predictions['anomaly_probability'] > 0.4:
                        analysis_results['anomaly_alert'] = {
                            'level': 'medium',
                            'message': 'Slightly unusual usage pattern',
                            'probability': predictions['anomaly_probability']
                        }
            
            # Usage assessment with AI enhancement
            water_status, electricity_status, gas_status = self._assess_usage_with_ai(
                water_gallons, electricity_kwh, gas_cubic_m
            )
            
            analysis_results['status'] = {
                'water': water_status,
                'electricity': electricity_status,
                'gas': gas_status
            }
            
            # Generate AI recommendations
            recommendations = self._generate_usage_recommendations(
                water_gallons, electricity_kwh, gas_cubic_m
            )
            analysis_results['recommendations'] = recommendations
            
            # Efficiency score
            efficiency_score = self._calculate_ai_efficiency_score(
                water_gallons, electricity_kwh, gas_cubic_m
            )
            analysis_results['efficiency_score'] = efficiency_score
            
            return analysis_results
            
        except Exception as e:
            print(f"Error in AI analysis: {e}")
            return {'error': str(e)}
    
    def _assess_usage_with_ai(self, water_gallons, electricity_kwh, gas_cubic_m):
        """Enhanced usage assessment with AI insights"""
        # Base assessment
        normal_water = (3000, 12000)
        normal_electricity = (300, 800)
        normal_gas = (50, 150)
        
        # AI-enhanced thresholds based on patterns
        if self.models_trained:
            try:
                # Get historical patterns
                historical_data = self._load_historical_data()
                if len(historical_data) > 10:
                    patterns = usage_predictor.analyze_usage_patterns(historical_data)
                    
                    # Adjust thresholds based on user's historical patterns
                    df = pd.DataFrame(historical_data)
                    user_avg_water = df['water_gallons'].mean()
                    user_avg_electricity = df['electricity_kwh'].mean()
                    user_avg_gas = df['gas_cubic_m'].mean()
                    
                    # Personalized thresholds (±30% of user average)
                    normal_water = (user_avg_water * 0.7, user_avg_water * 1.3)
                    normal_electricity = (user_avg_electricity * 0.7, user_avg_electricity * 1.3)
                    normal_gas = (user_avg_gas * 0.7, user_avg_gas * 1.3)
            except:
                pass  # Fall back to default thresholds
        
        # Assess with enhanced thresholds
        water_status = "Low" if water_gallons < normal_water[0] else "High" if water_gallons > normal_water[1] else "Normal"
        electricity_status = "Low" if electricity_kwh < normal_electricity[0] else "High" if electricity_kwh > normal_electricity[1] else "Normal"
        gas_status = "Low" if gas_cubic_m < normal_gas[0] else "High" if gas_cubic_m > normal_gas[1] else "Normal"
        
        return water_status, electricity_status, gas_status
    
    def _generate_usage_recommendations(self, water_gallons, electricity_kwh, gas_cubic_m):
        """Generate AI-powered usage recommendations"""
        recommendations = []
        
        # Water recommendations
        if water_gallons > 10000:
            recommendations.append({
                'category': 'Water Conservation',
                'priority': 'High',
                'message': 'High water usage detected. Consider checking for leaks and installing water-efficient fixtures.',
                'potential_savings': f'${(water_gallons - 8000) * 0.01:.2f}/month'
            })
        elif water_gallons < 2000:
            recommendations.append({
                'category': 'Water Usage',
                'priority': 'Medium',
                'message': 'Very low water usage. Verify meter readings and check for any issues.',
                'note': 'Unusually low usage may indicate meter problems'
            })
        
        # Electricity recommendations
        if electricity_kwh > 900:
            recommendations.append({
                'category': 'Energy Efficiency',
                'priority': 'High',
                'message': 'High electricity usage. Consider energy audit and LED lighting upgrade.',
                'potential_savings': f'${(electricity_kwh - 600) * 0.12:.2f}/month'
            })
        elif electricity_kwh < 200:
            recommendations.append({
                'category': 'Energy Usage',
                'priority': 'Low',
                'message': 'Excellent energy efficiency! Continue current practices.',
                'note': 'You are using 30% less energy than average'
            })
        
        # Gas recommendations
        if gas_cubic_m > 150:
            recommendations.append({
                'category': 'Gas Efficiency',
                'priority': 'Medium',
                'message': 'High gas usage. Check insulation and consider thermostat programming.',
                'potential_savings': f'${(gas_cubic_m - 100) * 0.85:.2f}/month'
            })
        
        # Seasonal recommendations
        current_month = datetime.now().month
        if current_month in [12, 1, 2]:  # Winter
            recommendations.append({
                'category': 'Seasonal',
                'priority': 'Medium',
                'message': 'Winter season: Monitor heating efficiency and seal air leaks.',
                'tip': 'Lower thermostat by 2°F to save 10-20% on heating costs'
            })
        elif current_month in [6, 7, 8]:  # Summer
            recommendations.append({
                'category': 'Seasonal',
                'priority': 'Medium',
                'message': 'Summer season: Optimize cooling and use fans to reduce AC load.',
                'tip': 'Raise thermostat by 2°F to save 10-20% on cooling costs'
            })
        
        return recommendations
    
    def _calculate_ai_efficiency_score(self, water_gallons, electricity_kwh, gas_cubic_m):
        """Calculate AI-enhanced efficiency score"""
        # Base efficiency calculation
        base_score = 100
        
        # Penalties for high usage
        if water_gallons > 10000:
            base_score -= (water_gallons - 10000) / 1000 * 5
        if electricity_kwh > 800:
            base_score -= (electricity_kwh - 800) / 100 * 10
        if gas_cubic_m > 120:
            base_score -= (gas_cubic_m - 120) / 20 * 5
        
        # Bonuses for efficient usage
        if water_gallons < 6000:
            base_score += 10
        if electricity_kwh < 500:
            base_score += 15
        if gas_cubic_m < 80:
            base_score += 10
        
        # AI enhancement: compare with historical patterns
        if self.models_trained:
            try:
                historical_data = self._load_historical_data()
                if len(historical_data) > 5:
                    patterns = usage_predictor.analyze_usage_patterns(historical_data)
                    
                    # Adjust score based on trends
                    if patterns.get('efficiency_score', 50) > 70:
                        base_score += 5  # Bonus for historically efficient user
                    
                    # Trend bonuses
                    trends = patterns.get('usage_trends', {})
                    if trends.get('water_trend') == 'decreasing':
                        base_score += 5
                    if trends.get('electricity_trend') == 'decreasing':
                        base_score += 5
                    if trends.get('gas_trend') == 'decreasing':
                        base_score += 5
            except:
                pass
        
        return max(0, min(100, round(base_score, 1)))
    
    def analyze_material_with_ai(self, material_name):
        """Analyze material with AI recommendations"""
        try:
            # Get sustainability analysis
            sustainability_analysis = recommendation_engine.analyze_material_sustainability(material_name)
            
            # Get historical material data
            material_data = db.find_material(material_name)
            
            # Enhanced analysis
            analysis = {
                'material_name': material_name,
                'sustainability_score': sustainability_analysis['sustainability_score'],
                'environmental_impact': sustainability_analysis['environmental_impact'],
                'ai_recommendations': sustainability_analysis['recommendations'],
                'reuse_suggestions': material_data.reuse_tip if material_data else "No specific reuse tips available",
                'recycle_instructions': material_data.recycle_tip if material_data else "No specific recycling instructions available"
            }
            
            # Add AI-generated additional insights
            if sustainability_analysis['sustainability_score'] < 4:
                analysis['priority_action'] = 'High - Consider alternatives or enhanced disposal methods'
            elif sustainability_analysis['sustainability_score'] < 7:
                analysis['priority_action'] = 'Medium - Follow recommended practices'
            else:
                analysis['priority_action'] = 'Low - Continue current practices'
            
            return analysis
            
        except Exception as e:
            return {'error': f'Material analysis failed: {str(e)}'}
    
    def get_personalized_recommendations(self):
        """Get personalized sustainability recommendations"""
        try:
            # Get user's usage history
            usage_data = self._load_historical_data()
            
            # Get material search history
            material_history = db.get_popular_materials(limit=20)
            material_data = [{'name': m.name, 'search_count': m.search_count} for m in material_history]
            
            # Generate personalized recommendations
            recommendations = recommendation_engine.generate_personalized_recommendations(
                usage_data, material_data
            )
            
            return recommendations
            
        except Exception as e:
            return {'error': f'Recommendation generation failed: {str(e)}'}
    
    def get_usage_insights(self):
        """Get comprehensive usage insights"""
        try:
            if not self.models_trained:
                return {'message': 'AI models not yet trained. Please add some usage data first.'}
            
            # Get historical data
            historical_data = self._load_historical_data()
            
            if len(historical_data) < 5:
                return {'message': 'Need more data for comprehensive insights. Please add more usage records.'}
            
            # Analyze patterns
            patterns = usage_predictor.analyze_usage_patterns(historical_data)
            
            # Get recent data for predictions
            recent_data = historical_data[-10:] if len(historical_data) >= 10 else historical_data
            
            insights = {
                'usage_patterns': patterns,
                'model_performance': self.model_performance,
                'data_quality': {
                    'total_records': len(historical_data),
                    'date_range': f"{historical_data[0]['timestamp'].strftime('%Y-%m-%d')} to {historical_data[-1]['timestamp'].strftime('%Y-%m-%d')}" if historical_data else "No data"
                },
                'last_training': self.last_training_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_training_time else "Never"
            }
            
            # Add predictions if available
            if recent_data:
                try:
                    predictions = usage_predictor.predict_usage(recent_data[-1])
                    if predictions:
                        insights['next_period_predictions'] = predictions
                except:
                    pass
            
            return insights
            
        except Exception as e:
            return {'error': f'Insights generation failed: {str(e)}'}
    
    def retrain_models_if_needed(self):
        """Retrain models if enough new data is available"""
        try:
            # Check if retraining is needed
            if self.last_training_time is None:
                return self.initialize_ai_system()
            
            # Retrain if more than 24 hours have passed and we have new data
            if datetime.now() - self.last_training_time > timedelta(hours=24):
                historical_data = self._load_historical_data()
                if len(historical_data) > 0:
                    return self.train_models(historical_data)
            
            return True, "Models are up to date"
            
        except Exception as e:
            return False, f"Retraining check failed: {str(e)}"


# Initialize global AI data processor
ai_processor = AIDataProcessor()