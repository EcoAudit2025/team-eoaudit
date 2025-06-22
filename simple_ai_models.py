import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, accuracy_score
import joblib
import os
from datetime import datetime, timedelta

class EcoAuditAI:
    """Simplified AI system for EcoAudit using only scikit-learn"""
    
    def __init__(self):
        self.water_model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.electricity_model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.gas_model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.anomaly_detector = RandomForestClassifier(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_performance = {}
        
    def prepare_features(self, data):
        """Prepare features for ML models from usage data"""
        if isinstance(data, dict):
            data = [data]
        
        features = []
        for record in data:
            timestamp = record['timestamp'] if isinstance(record['timestamp'], datetime) else pd.to_datetime(record['timestamp'])
            
            # Time-based features
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            month = timestamp.month
            day_of_month = timestamp.day
            
            # Usage features
            water = float(record['water_gallons'])
            electricity = float(record['electricity_kwh'])
            gas = float(record['gas_cubic_m'])
            
            # Derived features
            total_usage = water + electricity + gas
            water_ratio = water / max(total_usage, 1)
            electricity_ratio = electricity / max(total_usage, 1)
            gas_ratio = gas / max(total_usage, 1)
            
            feature_row = [
                hour, day_of_week, month, day_of_month,
                water, electricity, gas,
                total_usage, water_ratio, electricity_ratio, gas_ratio
            ]
            features.append(feature_row)
            
        return np.array(features)
    
    def generate_synthetic_data(self, n_samples=100):
        """Generate realistic synthetic training data - only for model training, not user display"""
        np.random.seed(42)
        synthetic_data = []
        base_date = datetime.now() - timedelta(days=n_samples)
        
        for i in range(n_samples):
            timestamp = base_date + timedelta(days=i)
            hour = timestamp.hour
            month = timestamp.month
            
            # More realistic and modest baseline values
            water_base = 5000 + 1500 * np.sin(2 * np.pi * month / 12)
            water_daily = 200 * (1 + np.sin(2 * np.pi * hour / 24))
            water = max(2000, water_base + water_daily + np.random.normal(0, 400))
            
            electricity_base = 400 + 100 * np.sin(2 * np.pi * month / 12)
            electricity_daily = 50 * (1 if 6 <= hour <= 22 else 0.5)
            electricity = max(150, electricity_base + electricity_daily + np.random.normal(0, 50))
            
            gas_base = 70 + 30 * np.cos(2 * np.pi * month / 12)
            gas = max(20, gas_base + np.random.normal(0, 15))
            
            synthetic_data.append({
                'timestamp': timestamp,
                'water_gallons': water,
                'electricity_kwh': electricity,
                'gas_cubic_m': gas,
                'water_status': 'Normal',
                'electricity_status': 'Normal',
                'gas_status': 'Normal'
            })
        
        return synthetic_data
    
    def create_anomaly_labels(self, data):
        """Create anomaly labels for training"""
        labels = []
        for record in data:
            water = record['water_gallons']
            electricity = record['electricity_kwh']
            gas = record['gas_cubic_m']
            
            # Define anomaly conditions
            is_anomaly = (
                water > 15000 or water < 1000 or
                electricity > 1200 or electricity < 100 or
                gas > 200 or gas < 10
            )
            labels.append(1 if is_anomaly else 0)
        return np.array(labels)
    
    def train_models(self, data):
        """Train all AI models"""
        try:
            # Validate input data
            if not data or len(data) == 0:
                self.is_trained = False
                return (False, "No data available for training")
            
            # Use synthetic data if not enough real data
            if len(data) < 20:
                synthetic_data = self.generate_synthetic_data(80)
                data = data + synthetic_data
            
            # Validate that we have enough samples
            if len(data) < 10:
                self.is_trained = False
                return (False, "Insufficient data for training")
            
            # Prepare features and targets
            features = self.prepare_features(data)
            if features.shape[0] == 0:
                self.is_trained = False
                return (False, "No valid features could be extracted")
                
            features_scaled = self.scaler.fit_transform(features)
            
            water_targets = [float(record['water_gallons']) for record in data]
            electricity_targets = [float(record['electricity_kwh']) for record in data]
            gas_targets = [float(record['gas_cubic_m']) for record in data]
            anomaly_labels = self.create_anomaly_labels(data)
            
            # Ensure we have enough samples for splitting
            min_samples_for_split = 4
            if len(data) < min_samples_for_split:
                # Train on all data if too few samples
                X_train = X_test = features_scaled
                y_water_train = y_water_test = water_targets
                y_elec_train = y_elec_test = electricity_targets
                y_gas_train = y_gas_test = gas_targets
                y_anomaly_train = y_anomaly_test = anomaly_labels
            else:
                # Split data
                test_size = min(0.3, max(0.1, 1.0 / len(data)))
                X_train, X_test, y_water_train, y_water_test = train_test_split(
                    features_scaled, water_targets, test_size=test_size, random_state=42
                )
                _, _, y_elec_train, y_elec_test = train_test_split(
                    features_scaled, electricity_targets, test_size=test_size, random_state=42
                )
                _, _, y_gas_train, y_gas_test = train_test_split(
                    features_scaled, gas_targets, test_size=test_size, random_state=42
                )
                _, _, y_anomaly_train, y_anomaly_test = train_test_split(
                    features_scaled, anomaly_labels, test_size=test_size, random_state=42
                )
            
            # Train models with error handling
            self.water_model.fit(X_train, y_water_train)
            self.electricity_model.fit(X_train, y_elec_train)
            self.gas_model.fit(X_train, y_gas_train)
            self.anomaly_detector.fit(X_train, y_anomaly_train)
            
            self.is_trained = True
            
            # Calculate performance metrics only if we have test data
            if len(X_test) > 0 and len(y_water_test) > 0:
                water_pred = self.water_model.predict(X_test)
                elec_pred = self.electricity_model.predict(X_test)
                gas_pred = self.gas_model.predict(X_test)
                anomaly_pred = self.anomaly_detector.predict(X_test)
                
                self.model_performance = {
                    'water_rmse': np.sqrt(mean_squared_error(y_water_test, water_pred)),
                    'electricity_rmse': np.sqrt(mean_squared_error(y_elec_test, elec_pred)),
                    'gas_rmse': np.sqrt(mean_squared_error(y_gas_test, gas_pred)),
                    'anomaly_accuracy': accuracy_score(y_anomaly_test, anomaly_pred),
                    'training_samples': len(data)
                }
            else:
                self.model_performance = {
                    'training_samples': len(data),
                    'note': 'Trained on full dataset due to small sample size'
                }
            
            return (True, f"Models trained with {len(data)} samples")
            
        except Exception as e:
            self.is_trained = False
            return (False, f"Training failed: {str(e)}")
    
    def predict_usage(self, current_data):
        """Predict future usage and detect anomalies"""
        if not self.is_trained:
            return None
        
        features = self.prepare_features([current_data])
        features_scaled = self.scaler.transform(features)
        
        # Get predictions
        water_pred = self.water_model.predict(features_scaled)[0]
        electricity_pred = self.electricity_model.predict(features_scaled)[0]
        gas_pred = self.gas_model.predict(features_scaled)[0]
        
        # Get anomaly probability
        anomaly_prob = self.anomaly_detector.predict_proba(features_scaled)[0]
        anomaly_probability = anomaly_prob[1] if len(anomaly_prob) > 1 else 0.0
        
        return {
            'water_prediction': max(0, water_pred),
            'electricity_prediction': max(0, electricity_pred),
            'gas_prediction': max(0, gas_pred),
            'anomaly_probability': float(anomaly_probability)
        }
    
    def analyze_usage_patterns(self, data):
        """Analyze usage patterns and trends"""
        if len(data) == 0:
            return {}
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        
        # Peak usage analysis
        peak_hours = {}
        if len(df) > 5:
            try:
                peak_hours = {
                    'water': int(df.groupby('hour')['water_gallons'].mean().idxmax()),
                    'electricity': int(df.groupby('hour')['electricity_kwh'].mean().idxmax()),
                    'gas': int(df.groupby('hour')['gas_cubic_m'].mean().idxmax())
                }
            except:
                peak_hours = {'water': 12, 'electricity': 18, 'gas': 8}
        
        # Trend analysis
        trends = {}
        if len(df) > 3:
            time_series = pd.Series(range(len(df)))
            trends = {
                'water_trend': self._get_trend(df['water_gallons'], time_series),
                'electricity_trend': self._get_trend(df['electricity_kwh'], time_series),
                'gas_trend': self._get_trend(df['gas_cubic_m'], time_series)
            }
        
        # Efficiency score
        efficiency_score = self._calculate_efficiency_score(df)
        
        return {
            'peak_usage_hours': peak_hours,
            'usage_trends': trends,
            'efficiency_score': efficiency_score,
            'total_records': len(df),
            'date_range': f"{df['timestamp'].min().strftime('%Y-%m-%d')} to {df['timestamp'].max().strftime('%Y-%m-%d')}" if len(df) > 0 else "No data"
        }
    
    def _get_trend(self, series, time_series):
        """Calculate trend direction"""
        try:
            correlation = series.corr(time_series)
            if correlation > 0.1:
                return 'increasing'
            elif correlation < -0.1:
                return 'decreasing'
            else:
                return 'stable'
        except:
            return 'stable'
    
    def _calculate_efficiency_score(self, df):
        """Calculate efficiency score based on usage patterns"""
        if len(df) == 0:
            return 50.0
        
        try:
            # Normalize against reasonable baselines
            water_avg = df['water_gallons'].mean()
            electricity_avg = df['electricity_kwh'].mean()
            gas_avg = df['gas_cubic_m'].mean()
            
            # Calculate efficiency (lower usage = higher efficiency)
            water_efficiency = max(0, 100 - (water_avg - 6000) / 100)
            electricity_efficiency = max(0, 100 - (electricity_avg - 500) / 10)
            gas_efficiency = max(0, 100 - (gas_avg - 80) / 2)
            
            # Weighted average
            overall_efficiency = (water_efficiency * 0.4 + electricity_efficiency * 0.4 + gas_efficiency * 0.2)
            return max(0, min(100, round(overall_efficiency, 1)))
        except:
            return 50.0
    
    def assess_usage(self, water_gallons, electricity_kwh, gas_cubic_m, historical_data=None):
        """Enhanced usage assessment with intelligent value analysis"""
        # Determine status with detailed understanding of values
        water_status = self._assess_water_usage(water_gallons, historical_data)
        electricity_status = self._assess_electricity_usage(electricity_kwh, historical_data)
        gas_status = self._assess_gas_usage(gas_cubic_m, historical_data)
        
        return water_status, electricity_status, gas_status
    
    def assess_usage_with_context(self, water_gallons, electricity_kwh, gas_cubic_m, user=None, historical_data=None):
        """Enhanced usage assessment with user context and energy features"""
        # Get user-specific context
        household_size = getattr(user, 'household_size', 1) if user else 1
        housing_type = getattr(user, 'housing_type', 'Unknown') if user else 'Unknown'
        location_type = getattr(user, 'location_type', 'Unknown') if user else 'Unknown'
        climate_zone = getattr(user, 'climate_zone', 'Unknown') if user else 'Unknown'
        
        # Parse energy features
        energy_features = []
        if user:
            try:
                import json
                energy_features_raw = getattr(user, 'energy_features', '[]') or '[]'
                energy_features = json.loads(energy_features_raw) if energy_features_raw else []
            except:
                energy_features = []
        
        # Adjust thresholds based on context
        water_threshold_multiplier = 1.0
        electricity_threshold_multiplier = 1.0
        gas_threshold_multiplier = 1.0
        
        # Household size adjustments
        if household_size > 1:
            water_threshold_multiplier *= (household_size * 0.7)  # Not linear scaling
            electricity_threshold_multiplier *= (household_size * 0.8)
            gas_threshold_multiplier *= (household_size * 0.75)
        
        # Climate zone adjustments
        if 'Tropical' in climate_zone or 'Hot' in climate_zone:
            electricity_threshold_multiplier *= 1.3  # More AC usage
            gas_threshold_multiplier *= 0.8  # Less heating
        elif 'Cold' in climate_zone or 'Continental' in climate_zone:
            electricity_threshold_multiplier *= 1.1  # Some electric heating
            gas_threshold_multiplier *= 1.4  # More heating
        
        # Housing type adjustments
        if 'House' in housing_type:
            electricity_threshold_multiplier *= 1.2  # Larger space
            gas_threshold_multiplier *= 1.3  # More heating area
        elif 'Apartment' in housing_type:
            electricity_threshold_multiplier *= 0.8  # Smaller space
            gas_threshold_multiplier *= 0.7  # Shared heating
        
        # Energy features adjustments (lower thresholds for efficient homes)
        efficiency_factor = 1.0
        for feature in energy_features:
            if "LED" in feature:
                efficiency_factor *= 0.9  # 10% lower electricity threshold
            elif "Smart Thermostat" in feature:
                efficiency_factor *= 0.85  # 15% lower for HVAC
            elif "Energy Star" in feature:
                efficiency_factor *= 0.9  # 10% lower overall
            elif "Solar" in feature:
                efficiency_factor *= 0.7  # 30% lower electricity expectation
            elif "Insulation" in feature:
                efficiency_factor *= 0.8  # 20% lower heating/cooling
        
        electricity_threshold_multiplier *= efficiency_factor
        gas_threshold_multiplier *= efficiency_factor
        
        # Apply contextual assessment
        water_status = self._assess_water_usage_contextual(water_gallons, water_threshold_multiplier, historical_data)
        electricity_status = self._assess_electricity_usage_contextual(electricity_kwh, electricity_threshold_multiplier, historical_data)
        gas_status = self._assess_gas_usage_contextual(gas_cubic_m, gas_threshold_multiplier, historical_data)
        
        return water_status, electricity_status, gas_status
    
    def _assess_water_usage(self, water_gallons, historical_data=None):
        """Intelligent water usage assessment based on actual values - corrected thresholds"""
        if water_gallons <= 10:      # Very low usage like 3.5 gallons
            return "Excellent"
        elif water_gallons <= 25:    # Low usage
            return "Very Good"
        elif water_gallons <= 50:    # Moderate usage
            return "Good"
        elif water_gallons <= 100:   # Higher usage
            return "Fair"
        elif water_gallons <= 200:   # High usage
            return "Poor"
        else:                        # Very high usage
            return "Very Poor"
    
    def _assess_electricity_usage(self, electricity_kwh, historical_data=None):
        """Intelligent electricity usage assessment based on actual values"""
        if electricity_kwh <= 200:
            return "Excellent"
        elif electricity_kwh <= 400:
            return "Very Good"
        elif electricity_kwh <= 600:
            return "Good"
        elif electricity_kwh <= 800:
            return "Fair"
        elif electricity_kwh <= 1000:
            return "Poor"
        else:
            return "Very Poor"
    
    def _assess_gas_usage(self, gas_cubic_m, historical_data=None):
        """Intelligent gas usage assessment based on actual values"""
        if gas_cubic_m <= 20:
            return "Excellent"
        elif gas_cubic_m <= 40:
            return "Very Good"
        elif gas_cubic_m <= 60:
            return "Good"
        elif gas_cubic_m <= 80:
            return "Fair"
        elif gas_cubic_m <= 100:
            return "Poor"
        else:
            return "Very Poor"
    
    def generate_recommendations(self, water_gallons, electricity_kwh, gas_cubic_m, analysis_results=None):
        """Generate intelligent AI-powered recommendations based on actual values"""
        recommendations = []
        
        # Intelligent water recommendations with specific value analysis
        if water_gallons > 300:
            recommendations.append(f"URGENT: Water usage at {water_gallons} gallons is critically high. Immediate actions: check for leaks, install low-flow showerheads (save 2.5 gal/min), limit showers to 5 minutes. Potential savings: ${(water_gallons-200)*0.004:.0f}/month.")
        elif water_gallons > 200:
            recommendations.append(f"Water consumption at {water_gallons} gallons needs attention. Install water-efficient appliances, fix dripping faucets immediately. Target: reduce to under 150 gallons monthly.")
        elif water_gallons > 150:
            recommendations.append(f"Water usage at {water_gallons} gallons is moderate. Run dishwasher only when full, take shorter showers, use cold water for laundry to optimize efficiency.")
        elif water_gallons > 100:
            recommendations.append(f"Good water efficiency at {water_gallons} gallons. Fine-tune by collecting rainwater for plants and using greywater systems if possible.")
        elif water_gallons > 50:
            recommendations.append(f"Very good water conservation at {water_gallons} gallons. You're approaching excellent levels - continue current practices.")
        else:
            recommendations.append(f"Outstanding water conservation at {water_gallons} gallons! You're setting an exemplary standard for sustainable water use.")
        
        # Intelligent electricity recommendations with specific value analysis
        if electricity_kwh > 1000:
            recommendations.append(f"CRITICAL: Electricity usage at {electricity_kwh} kWh requires immediate action. Replace all bulbs with LEDs (75% savings), use programmable thermostat, unplug devices on standby. Potential savings: ${(electricity_kwh-600)*0.12:.0f}/month.")
        elif electricity_kwh > 800:
            recommendations.append(f"High electricity consumption at {electricity_kwh} kWh. Focus on HVAC efficiency: seal air leaks, use ceiling fans, adjust thermostat 2-3 degrees, clean/replace filters monthly.")
        elif electricity_kwh > 600:
            recommendations.append(f"Electricity usage at {electricity_kwh} kWh has improvement potential. Use smart power strips, air-dry clothes, upgrade to Energy Star appliances for major reductions.")
        elif electricity_kwh > 400:
            recommendations.append(f"Moderate electricity consumption at {electricity_kwh} kWh. Optimize with motion sensors for lighting, use natural light during day, cook multiple items together.")
        elif electricity_kwh > 200:
            recommendations.append(f"Good energy efficiency at {electricity_kwh} kWh. You're approaching exemplary conservation - consider solar panels for energy independence.")
        else:
            recommendations.append(f"Exceptional energy efficiency at {electricity_kwh} kWh! Your electrical conservation practices are outstanding and climate-positive.")
        
        # Intelligent gas recommendations with specific value analysis
        if gas_cubic_m > 120:
            recommendations.append(f"High gas consumption at {gas_cubic_m} m³. Priority improvements: add attic/wall insulation (30% savings), seal windows/doors, lower thermostat to 68°F, upgrade to high-efficiency furnace. Potential savings: ${(gas_cubic_m-60)*0.80:.0f}/month.")
        elif gas_cubic_m > 80:
            recommendations.append(f"Gas usage at {gas_cubic_m} m³ needs optimization. Service heating equipment annually, use microwave for small heating tasks, cook with lids on pots, consider zone heating.")
        elif gas_cubic_m > 60:
            recommendations.append(f"Gas consumption at {gas_cubic_m} m³ is moderate. Dress warmer indoors (each degree saves 6-8%), use exhaust fans minimally in winter, cook multiple items simultaneously.")
        elif gas_cubic_m > 40:
            recommendations.append(f"Good gas efficiency at {gas_cubic_m} m³. Continue current practices and consider smart thermostats for automated optimization.")
        elif gas_cubic_m > 20:
            recommendations.append(f"Excellent gas conservation at {gas_cubic_m} m³. Your heating and cooking practices are highly efficient and environmentally responsible.")
        else:
            recommendations.append(f"Outstanding gas efficiency at {gas_cubic_m} m³! Minimal gas consumption demonstrates exceptional conservation skills.")
        
        # Calculate overall sustainability score and add comprehensive insight
        total_impact = (water_gallons/3 + electricity_kwh/10 + gas_cubic_m*2)
        if total_impact < 100:
            recommendations.append(f"SUSTAINABILITY CHAMPION: Your combined utility footprint is exceptional. Consider sharing your conservation strategies with neighbors and joining local environmental groups.")
        elif total_impact < 200:
            recommendations.append(f"ENVIRONMENTAL PERFORMER: Your overall sustainability is commendable. Focus improvements on your highest usage utility for maximum impact.")
        elif total_impact < 350:
            recommendations.append(f"IMPROVEMENT OPPORTUNITY: Systematic conservation across all utilities could reduce your environmental impact by 30-50%. Start with highest consumption area.")
        else:
            recommendations.append(f"ACTION REQUIRED: Comprehensive conservation strategy needed. Prioritize immediate efficiency improvements - potential for significant environmental and cost benefits.")
        
        # Add carbon footprint insight with specific calculations
        carbon_water = water_gallons * 0.002
        carbon_electricity = electricity_kwh * 0.4
        carbon_gas = gas_cubic_m * 2.2
        total_carbon = carbon_water + carbon_electricity + carbon_gas
        
        if total_carbon > 500:
            recommendations.append(f"Carbon Impact: {total_carbon:.0f} kg CO2/month is high. Focus on your largest source: {'electricity' if carbon_electricity == max(carbon_water, carbon_electricity, carbon_gas) else 'gas' if carbon_gas == max(carbon_water, carbon_electricity, carbon_gas) else 'water'} for maximum climate benefit.")
        elif total_carbon > 300:
            recommendations.append(f"Carbon Impact: {total_carbon:.0f} kg CO2/month is moderate. Strategic improvements could achieve low-carbon lifestyle targets.")
        else:
            recommendations.append(f"Carbon Impact: Excellent at {total_carbon:.0f} kg CO2/month. You're contributing positively to climate goals and setting an example for others.")
        
        return recommendations
    
    def _assess_water_usage_contextual(self, water_gallons, threshold_multiplier, historical_data=None):
        """Water usage assessment with contextual thresholds - corrected base values"""
        base_thresholds = [10, 25, 50, 100, 200]  # Corrected realistic thresholds
        adjusted_thresholds = [t * threshold_multiplier for t in base_thresholds]
        
        if water_gallons <= adjusted_thresholds[0]:
            return "Excellent"
        elif water_gallons <= adjusted_thresholds[1]:
            return "Very Good"
        elif water_gallons <= adjusted_thresholds[2]:
            return "Good"
        elif water_gallons <= adjusted_thresholds[3]:
            return "Fair"
        elif water_gallons <= adjusted_thresholds[4]:
            return "Poor"
        else:
            return "Needs Improvement"
    
    def _assess_electricity_usage_contextual(self, electricity_kwh, threshold_multiplier, historical_data=None):
        """Electricity usage assessment with contextual thresholds"""
        base_thresholds = [200, 400, 600, 800, 1000]
        adjusted_thresholds = [t * threshold_multiplier for t in base_thresholds]
        
        if electricity_kwh <= adjusted_thresholds[0]:
            return "Excellent"
        elif electricity_kwh <= adjusted_thresholds[1]:
            return "Very Good"
        elif electricity_kwh <= adjusted_thresholds[2]:
            return "Good"
        elif electricity_kwh <= adjusted_thresholds[3]:
            return "Fair"
        elif electricity_kwh <= adjusted_thresholds[4]:
            return "Poor"
        else:
            return "Needs Improvement"
    
    def _assess_gas_usage_contextual(self, gas_cubic_m, threshold_multiplier, historical_data=None):
        """Gas usage assessment with contextual thresholds"""
        base_thresholds = [20, 40, 60, 80, 100]
        adjusted_thresholds = [t * threshold_multiplier for t in base_thresholds]
        
        if gas_cubic_m <= adjusted_thresholds[0]:
            return "Excellent"
        elif gas_cubic_m <= adjusted_thresholds[1]:
            return "Very Good"
        elif gas_cubic_m <= adjusted_thresholds[2]:
            return "Good"
        elif gas_cubic_m <= adjusted_thresholds[3]:
            return "Fair"
        elif gas_cubic_m <= adjusted_thresholds[4]:
            return "Poor"
        else:
            return "Needs Improvement"
    
    def generate_contextual_recommendations(self, water_gallons, electricity_kwh, gas_cubic_m, user=None):
        """Generate recommendations based on user context and energy features"""
        recommendations = self.generate_recommendations(water_gallons, electricity_kwh, gas_cubic_m)
        
        if not user:
            return recommendations
        
        # Get user context
        try:
            import json
            energy_features = json.loads(getattr(user, 'energy_features', '[]') or '[]')
            household_size = getattr(user, 'household_size', 1) or 1
            housing_type = getattr(user, 'housing_type', 'Unknown')
            climate_zone = getattr(user, 'climate_zone', 'Unknown')
        except:
            return recommendations
        
        # Add contextual recommendations
        contextual_recs = []
        
        # Energy features specific recommendations
        if energy_features:
            missing_features = []
            if not any("LED" in feature for feature in energy_features):
                missing_features.append("LED lighting")
            if not any("Thermostat" in feature for feature in energy_features):
                missing_features.append("smart thermostat")
            if not any("Energy Star" in feature for feature in energy_features):
                missing_features.append("Energy Star appliances")
            
            if missing_features and electricity_kwh > 400:
                contextual_recs.append(f"Consider adding {', '.join(missing_features)} to complement your existing efficiency features and further reduce your {electricity_kwh} kWh consumption.")
        
        # Climate-specific recommendations
        if 'Hot' in climate_zone or 'Tropical' in climate_zone:
            if electricity_kwh > 600:
                contextual_recs.append(f"In your {climate_zone.lower()} climate, focus on cooling efficiency: use ceiling fans, close blinds during peak sun hours, and set AC to 78°F to reduce your {electricity_kwh} kWh usage.")
        elif 'Cold' in climate_zone or 'Continental' in climate_zone:
            if gas_cubic_m > 80:
                contextual_recs.append(f"For your {climate_zone.lower()} climate, optimize heating: add weather stripping, use thermal curtains, and lower thermostat by 2°F to reduce your {gas_cubic_m} m³ gas consumption.")
        
        # Household size recommendations
        if household_size > 3:
            if water_gallons > 200:
                contextual_recs.append(f"With {household_size} people, coordinate shower schedules, teach children water conservation, and consider dual-flush toilets to manage your {water_gallons} gallon usage.")
            if electricity_kwh > 800:
                contextual_recs.append(f"Large households can reduce {electricity_kwh} kWh usage by designating device charging stations, using timer switches, and implementing 'lights out' policies.")
        
        # Combine original and contextual recommendations
        return recommendations + contextual_recs
        
        # Electricity recommendations
        if electricity_kwh > 900:
            savings = (electricity_kwh - 600) * 0.12
            recommendations.append({
                'category': 'Energy Efficiency',
                'priority': 'High',
                'message': 'High electricity usage. Consider LED lighting and energy-efficient appliances.',
                'potential_savings': f'${savings:.2f}/month',
                'impact': 'Reduce carbon footprint by 15-20%'
            })
        elif electricity_kwh < 300:
            recommendations.append({
                'category': 'Energy Usage',
                'priority': 'Low',
                'message': 'Excellent energy efficiency! Continue current practices.',
                'note': 'You are using 40% less energy than average'
            })
        
        # Gas recommendations
        if gas_cubic_m > 150:
            savings = (gas_cubic_m - 100) * 0.85
            recommendations.append({
                'category': 'Gas Efficiency',
                'priority': 'Medium',
                'message': 'High gas usage. Check insulation and consider programmable thermostat.',
                'potential_savings': f'${savings:.2f}/month',
                'impact': 'Improve home comfort and efficiency'
            })
        
        # Seasonal recommendations
        current_month = datetime.now().month
        if current_month in [12, 1, 2]:  # Winter
            recommendations.append({
                'category': 'Seasonal Tips',
                'priority': 'Medium',
                'message': 'Winter energy saving: Lower thermostat by 2°F when away.',
                'tip': 'Can save 10-20% on heating costs'
            })
        elif current_month in [6, 7, 8]:  # Summer
            recommendations.append({
                'category': 'Seasonal Tips',
                'priority': 'Medium',
                'message': 'Summer cooling tips: Use fans and raise AC temperature by 2°F.',
                'tip': 'Can save 10-20% on cooling costs'
            })
        
        return recommendations
    
    def save_models(self, path='models/'):
        """Save trained models"""
        os.makedirs(path, exist_ok=True)
        if self.is_trained:
            joblib.dump(self.water_model, f'{path}water_model.pkl')
            joblib.dump(self.electricity_model, f'{path}electricity_model.pkl')
            joblib.dump(self.gas_model, f'{path}gas_model.pkl')
            joblib.dump(self.anomaly_detector, f'{path}anomaly_model.pkl')
            joblib.dump(self.scaler, f'{path}scaler.pkl')
    
    def load_models(self, path='models/'):
        """Load trained models"""
        try:
            self.water_model = joblib.load(f'{path}water_model.pkl')
            self.electricity_model = joblib.load(f'{path}electricity_model.pkl')
            self.gas_model = joblib.load(f'{path}gas_model.pkl')
            self.anomaly_detector = joblib.load(f'{path}anomaly_model.pkl')
            self.scaler = joblib.load(f'{path}scaler.pkl')
            self.is_trained = True
            return True
        except:
            return False


class MaterialSustainabilityAI:
    """AI system for material sustainability analysis"""
    
    def __init__(self):
        self.sustainability_db = {
            'plastic': {'impact': 8.5, 'recyclability': 6.0, 'carbon': 9.0},
            'glass': {'impact': 5.0, 'recyclability': 9.5, 'carbon': 6.0},
            'metal': {'impact': 6.0, 'recyclability': 9.8, 'carbon': 7.5},
            'electronics': {'impact': 9.5, 'recyclability': 7.0, 'carbon': 9.8},
            'paper': {'impact': 4.0, 'recyclability': 8.5, 'carbon': 3.5},
            'cardboard': {'impact': 3.5, 'recyclability': 9.0, 'carbon': 3.0}
        }
    
    def analyze_material(self, material_name):
        """Analyze material sustainability"""
        material_lower = material_name.lower()
        
        # Find matching category
        category = None
        for cat in self.sustainability_db.keys():
            if cat in material_lower:
                category = cat
                break
        
        # Check for specific materials
        if not category:
            if any(word in material_lower for word in ['bottle', 'container', 'bag']):
                if 'glass' in material_lower:
                    category = 'glass'
                else:
                    category = 'plastic'
            elif any(word in material_lower for word in ['can', 'aluminum', 'steel']):
                category = 'metal'
            elif any(word in material_lower for word in ['phone', 'computer', 'battery']):
                category = 'electronics'
        
        if category:
            data = self.sustainability_db[category]
            sustainability_score = (
                (10 - data['impact']) * 0.4 +
                data['recyclability'] * 0.4 +
                (10 - data['carbon']) * 0.2
            )
            
            return {
                'sustainability_score': round(sustainability_score, 1),
                'environmental_impact': data['impact'],
                'recyclability': data['recyclability'],
                'carbon_footprint': data['carbon'],
                'category': category
            }
        else:
            # Default values for unknown materials
            return {
                'sustainability_score': 5.0,
                'environmental_impact': 5.0,  # Numeric default
                'recyclability': 5.0,  # Numeric default
                'carbon_footprint': 5.0,  # Numeric default
                'category': 'unknown'
            }


# Initialize global AI components
eco_ai = EcoAuditAI()
material_ai = MaterialSustainabilityAI()