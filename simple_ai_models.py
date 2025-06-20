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
        """Enhanced usage assessment with AI insights"""
        # Basic thresholds
        normal_water = (3000, 12000)
        normal_electricity = (300, 800)
        normal_gas = (50, 150)
        
        # Adjust thresholds based on user's historical patterns
        if historical_data and len(historical_data) > 5:
            df = pd.DataFrame(historical_data)
            user_water_avg = df['water_gallons'].mean()
            user_electricity_avg = df['electricity_kwh'].mean()
            user_gas_avg = df['gas_cubic_m'].mean()
            
            # Personalized thresholds (±25% of user average)
            normal_water = (user_water_avg * 0.75, user_water_avg * 1.25)
            normal_electricity = (user_electricity_avg * 0.75, user_electricity_avg * 1.25)
            normal_gas = (user_gas_avg * 0.75, user_gas_avg * 1.25)
        
        # Assess status
        water_status = "Low" if water_gallons < normal_water[0] else "High" if water_gallons > normal_water[1] else "Normal"
        electricity_status = "Low" if electricity_kwh < normal_electricity[0] else "High" if electricity_kwh > normal_electricity[1] else "Normal"
        gas_status = "Low" if gas_cubic_m < normal_gas[0] else "High" if gas_cubic_m > normal_gas[1] else "Normal"
        
        return water_status, electricity_status, gas_status
    
    def generate_recommendations(self, water_gallons, electricity_kwh, gas_cubic_m, analysis_results=None):
        """Generate AI-powered recommendations"""
        recommendations = []
        
        # Water recommendations
        if water_gallons > 10000:
            savings = (water_gallons - 8000) * 0.01
            recommendations.append({
                'category': 'Water Conservation',
                'priority': 'High',
                'message': 'High water usage detected. Consider checking for leaks and installing low-flow fixtures.',
                'potential_savings': f'${savings:.2f}/month',
                'impact': 'Environmental and cost savings'
            })
        elif water_gallons < 2000:
            recommendations.append({
                'category': 'Water Usage',
                'priority': 'Medium',
                'message': 'Very low water usage detected. Verify meter readings.',
                'note': 'Unusually low usage may indicate meter issues'
            })
        
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