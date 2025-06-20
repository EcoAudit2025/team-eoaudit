import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, accuracy_score, classification_report
import joblib
import os
from datetime import datetime, timedelta
# Simplified AI without TensorFlow for better compatibility
TF_AVAILABLE = False
import matplotlib.pyplot as plt
import seaborn as sns

class UtilityUsagePredictor:
    """AI model for predicting utility usage patterns and anomalies"""
    
    def __init__(self):
        self.water_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.electricity_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.gas_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.anomaly_detector = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        
    def prepare_features(self, data):
        """Prepare features for ML models"""
        features = []
        
        for _, row in data.iterrows():
            # Time-based features
            timestamp = pd.to_datetime(row['timestamp'])
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            month = timestamp.month
            day_of_month = timestamp.day
            
            # Usage ratios and patterns
            total_usage = row['water_gallons'] + row['electricity_kwh'] + row['gas_cubic_m']
            water_ratio = row['water_gallons'] / max(total_usage, 1)
            electricity_ratio = row['electricity_kwh'] / max(total_usage, 1)
            gas_ratio = row['gas_cubic_m'] / max(total_usage, 1)
            
            feature_row = [
                hour, day_of_week, month, day_of_month,
                row['water_gallons'], row['electricity_kwh'], row['gas_cubic_m'],
                total_usage, water_ratio, electricity_ratio, gas_ratio
            ]
            features.append(feature_row)
            
        return np.array(features)
    
    def train_models(self, data):
        """Train all AI models with historical data"""
        if len(data) < 10:
            # Generate synthetic training data for initial model
            synthetic_data = self._generate_synthetic_data()
            data = pd.concat([data, synthetic_data], ignore_index=True)
        
        features = self.prepare_features(data)
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features)
        
        # Prepare targets
        water_targets = data['water_gallons'].values
        electricity_targets = data['electricity_kwh'].values
        gas_targets = data['gas_cubic_m'].values
        
        # Create anomaly labels (simplified logic)
        anomaly_labels = self._create_anomaly_labels(data)
        
        # Split data
        X_train, X_test, y_water_train, y_water_test = train_test_split(
            features_scaled, water_targets, test_size=0.2, random_state=42
        )
        _, _, y_elec_train, y_elec_test = train_test_split(
            features_scaled, electricity_targets, test_size=0.2, random_state=42
        )
        _, _, y_gas_train, y_gas_test = train_test_split(
            features_scaled, gas_targets, test_size=0.2, random_state=42
        )
        _, _, y_anomaly_train, y_anomaly_test = train_test_split(
            features_scaled, anomaly_labels, test_size=0.2, random_state=42
        )
        
        # Train models
        self.water_model.fit(X_train, y_water_train)
        self.electricity_model.fit(X_train, y_elec_train)
        self.gas_model.fit(X_train, y_gas_train)
        self.anomaly_detector.fit(X_train, y_anomaly_train)
        
        self.is_trained = True
        
        # Calculate and return model performance
        water_pred = self.water_model.predict(X_test)
        elec_pred = self.electricity_model.predict(X_test)
        gas_pred = self.gas_model.predict(X_test)
        anomaly_pred = self.anomaly_detector.predict(X_test)
        
        performance = {
            'water_rmse': np.sqrt(mean_squared_error(y_water_test, water_pred)),
            'electricity_rmse': np.sqrt(mean_squared_error(y_elec_test, elec_pred)),
            'gas_rmse': np.sqrt(mean_squared_error(y_gas_test, gas_pred)),
            'anomaly_accuracy': accuracy_score(y_anomaly_test, anomaly_pred)
        }
        
        return performance
    
    def predict_usage(self, current_data):
        """Predict future utility usage"""
        if not self.is_trained:
            return None
            
        features = self.prepare_features(pd.DataFrame([current_data]))
        features_scaled = self.scaler.transform(features)
        
        predictions = {
            'water_prediction': float(self.water_model.predict(features_scaled)[0]),
            'electricity_prediction': float(self.electricity_model.predict(features_scaled)[0]),
            'gas_prediction': float(self.gas_model.predict(features_scaled)[0]),
            'anomaly_probability': float(self.anomaly_detector.predict_proba(features_scaled)[0][1])
        }
        
        return predictions
    
    def analyze_usage_patterns(self, data):
        """Analyze usage patterns using ML"""
        if len(data) == 0:
            return {}
            
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        
        analysis = {
            'peak_usage_hours': {
                'water': int(df.groupby('hour')['water_gallons'].mean().idxmax()),
                'electricity': int(df.groupby('hour')['electricity_kwh'].mean().idxmax()),
                'gas': int(df.groupby('hour')['gas_cubic_m'].mean().idxmax())
            },
            'usage_trends': {
                'water_trend': 'increasing' if df['water_gallons'].corr(pd.Series(range(len(df)))) > 0.1 else 'decreasing' if df['water_gallons'].corr(pd.Series(range(len(df)))) < -0.1 else 'stable',
                'electricity_trend': 'increasing' if df['electricity_kwh'].corr(pd.Series(range(len(df)))) > 0.1 else 'decreasing' if df['electricity_kwh'].corr(pd.Series(range(len(df)))) < -0.1 else 'stable',
                'gas_trend': 'increasing' if df['gas_cubic_m'].corr(pd.Series(range(len(df)))) > 0.1 else 'decreasing' if df['gas_cubic_m'].corr(pd.Series(range(len(df)))) < -0.1 else 'stable'
            },
            'efficiency_score': self._calculate_efficiency_score(df),
            'seasonal_patterns': self._detect_seasonal_patterns(df)
        }
        
        return analysis
    
    def _generate_synthetic_data(self):
        """Generate synthetic training data for initial model training"""
        np.random.seed(42)
        n_samples = 100
        
        synthetic_data = []
        base_date = datetime.now() - timedelta(days=100)
        
        for i in range(n_samples):
            timestamp = base_date + timedelta(days=i)
            
            # Simulate realistic usage patterns
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            month = timestamp.month
            
            # Water usage (seasonal and daily patterns)
            water_base = 8000 + 2000 * np.sin(2 * np.pi * month / 12)  # Seasonal
            water_daily = 1000 * np.sin(2 * np.pi * hour / 24)  # Daily pattern
            water = max(0, water_base + water_daily + np.random.normal(0, 500))
            
            # Electricity usage
            elec_base = 600 + 200 * np.sin(2 * np.pi * month / 12)
            elec_daily = 100 * (1 if 6 <= hour <= 22 else 0.3)  # Day/night pattern
            electricity = max(0, elec_base + elec_daily + np.random.normal(0, 50))
            
            # Gas usage (heating season pattern)
            gas_base = 100 + 80 * np.cos(2 * np.pi * month / 12)  # Winter heating
            gas = max(0, gas_base + np.random.normal(0, 20))
            
            synthetic_data.append({
                'timestamp': timestamp,
                'water_gallons': water,
                'electricity_kwh': electricity,
                'gas_cubic_m': gas,
                'water_status': 'Normal',
                'electricity_status': 'Normal',
                'gas_status': 'Normal'
            })
        
        return pd.DataFrame(synthetic_data)
    
    def _create_anomaly_labels(self, data):
        """Create anomaly labels for training"""
        labels = []
        for _, row in data.iterrows():
            # Simple anomaly detection based on extreme values
            is_anomaly = (
                row['water_gallons'] > 15000 or row['water_gallons'] < 1000 or
                row['electricity_kwh'] > 1200 or row['electricity_kwh'] < 100 or
                row['gas_cubic_m'] > 200 or row['gas_cubic_m'] < 10
            )
            labels.append(1 if is_anomaly else 0)
        return np.array(labels)
    
    def _calculate_efficiency_score(self, df):
        """Calculate overall efficiency score"""
        if len(df) == 0:
            return 50
            
        # Normalize usage values and calculate efficiency
        water_norm = (df['water_gallons'].mean() - 8000) / 8000
        elec_norm = (df['electricity_kwh'].mean() - 600) / 600
        gas_norm = (df['gas_cubic_m'].mean() - 100) / 100
        
        # Higher usage = lower efficiency
        efficiency = max(0, min(100, 100 - (water_norm + elec_norm + gas_norm) * 20))
        return round(efficiency, 1)
    
    def _detect_seasonal_patterns(self, df):
        """Detect seasonal usage patterns"""
        if len(df) < 4:
            return "Insufficient data for seasonal analysis"
            
        monthly_avg = df.groupby('month')[['water_gallons', 'electricity_kwh', 'gas_cubic_m']].mean()
        
        patterns = []
        if monthly_avg['water_gallons'].max() / monthly_avg['water_gallons'].min() > 1.5:
            patterns.append("Strong seasonal water usage variation")
        if monthly_avg['gas_cubic_m'].max() / monthly_avg['gas_cubic_m'].min() > 2.0:
            patterns.append("Winter heating pattern detected")
        if monthly_avg['electricity_kwh'].max() / monthly_avg['electricity_kwh'].min() > 1.3:
            patterns.append("Seasonal electricity usage variation")
            
        return patterns if patterns else ["Stable usage patterns across seasons"]
    
    def save_models(self, path='models/'):
        """Save trained models"""
        os.makedirs(path, exist_ok=True)
        joblib.dump(self.water_model, f'{path}water_model.pkl')
        joblib.dump(self.electricity_model, f'{path}electricity_model.pkl')
        joblib.dump(self.gas_model, f'{path}gas_model.pkl')
        joblib.dump(self.anomaly_detector, f'{path}anomaly_model.pkl')
        joblib.dump(self.scaler, f'{path}scaler.pkl')
        joblib.dump(self.label_encoder, f'{path}label_encoder.pkl')
    
    def load_models(self, path='models/'):
        """Load trained models"""
        try:
            self.water_model = joblib.load(f'{path}water_model.pkl')
            self.electricity_model = joblib.load(f'{path}electricity_model.pkl')
            self.gas_model = joblib.load(f'{path}gas_model.pkl')
            self.anomaly_detector = joblib.load(f'{path}anomaly_model.pkl')
            self.scaler = joblib.load(f'{path}scaler.pkl')
            self.label_encoder = joblib.load(f'{path}label_encoder.pkl')
            self.is_trained = True
            return True
        except:
            return False


class SustainabilityRecommendationEngine:
    """AI-powered sustainability recommendation system"""
    
    def __init__(self):
        self.recommendation_model = None
        self.material_embeddings = {}
        self._build_material_knowledge_base()
    
    def _build_material_knowledge_base(self):
        """Build knowledge base for materials and sustainability recommendations"""
        self.sustainability_knowledge = {
            'plastic': {
                'environmental_impact': 8.5,
                'recyclability': 6.0,
                'biodegradability': 1.0,
                'carbon_footprint': 9.0,
                'recommendations': [
                    'Switch to reusable alternatives when possible',
                    'Ensure proper recycling through designated programs',
                    'Consider plastic-free alternatives for single-use items'
                ]
            },
            'glass': {
                'environmental_impact': 5.0,
                'recyclability': 9.5,
                'biodegradability': 1.0,
                'carbon_footprint': 6.0,
                'recommendations': [
                    'Glass is infinitely recyclable - always recycle',
                    'Reuse glass containers for storage',
                    'Choose glass over plastic when possible'
                ]
            },
            'metal': {
                'environmental_impact': 6.0,
                'recyclability': 9.8,
                'biodegradability': 1.0,
                'carbon_footprint': 7.5,
                'recommendations': [
                    'Metals are highly valuable for recycling',
                    'Separate different types of metals for better recycling',
                    'Consider metal alternatives for durability'
                ]
            },
            'electronics': {
                'environmental_impact': 9.5,
                'recyclability': 7.0,
                'biodegradability': 1.0,
                'carbon_footprint': 9.8,
                'recommendations': [
                    'Use certified e-waste recycling programs',
                    'Extend device lifespan through proper maintenance',
                    'Consider refurbished electronics over new ones'
                ]
            }
        }
    
    def analyze_material_sustainability(self, material_name):
        """Analyze sustainability metrics for a material"""
        material_lower = material_name.lower()
        
        # Find matching category
        category = None
        for cat in self.sustainability_knowledge.keys():
            if cat in material_lower:
                category = cat
                break
        
        if not category:
            # Default analysis for unknown materials
            return {
                'sustainability_score': 5.0,
                'environmental_impact': 'Unknown - requires research',
                'recommendations': [
                    'Research proper disposal methods for this material',
                    'Look for manufacturer take-back programs',
                    'Consider more sustainable alternatives'
                ]
            }
        
        knowledge = self.sustainability_knowledge[category]
        
        # Calculate overall sustainability score
        sustainability_score = (
            (10 - knowledge['environmental_impact']) * 0.3 +
            knowledge['recyclability'] * 0.3 +
            knowledge['biodegradability'] * 0.2 +
            (10 - knowledge['carbon_footprint']) * 0.2
        )
        
        return {
            'sustainability_score': round(sustainability_score, 1),
            'environmental_impact': knowledge['environmental_impact'],
            'recyclability': knowledge['recyclability'],
            'carbon_footprint': knowledge['carbon_footprint'],
            'recommendations': knowledge['recommendations']
        }
    
    def generate_personalized_recommendations(self, usage_data, material_history):
        """Generate personalized sustainability recommendations based on usage patterns"""
        recommendations = []
        
        # Analyze usage patterns
        if usage_data:
            df = pd.DataFrame(usage_data)
            avg_water = df['water_gallons'].mean()
            avg_electricity = df['electricity_kwh'].mean()
            avg_gas = df['gas_cubic_m'].mean()
            
            # Water recommendations
            if avg_water > 10000:
                recommendations.append({
                    'category': 'Water Conservation',
                    'priority': 'High',
                    'recommendation': 'Install low-flow fixtures and fix any leaks to reduce water usage by 20-30%',
                    'estimated_savings': f'${(avg_water - 8000) * 0.01:.2f}/month'
                })
            
            # Electricity recommendations
            if avg_electricity > 800:
                recommendations.append({
                    'category': 'Energy Efficiency',
                    'priority': 'High',
                    'recommendation': 'Switch to LED lighting and energy-efficient appliances',
                    'estimated_savings': f'${(avg_electricity - 600) * 0.12:.2f}/month'
                })
            
            # Gas recommendations
            if avg_gas > 120:
                recommendations.append({
                    'category': 'Gas Efficiency',
                    'priority': 'Medium',
                    'recommendation': 'Improve home insulation and consider programmable thermostat',
                    'estimated_savings': f'${(avg_gas - 100) * 0.85:.2f}/month'
                })
        
        # Material-based recommendations
        if material_history:
            material_counts = {}
            for material in material_history:
                category = self._categorize_material(material['name'])
                material_counts[category] = material_counts.get(category, 0) + 1
            
            # Most frequent category
            if material_counts:
                top_category = max(material_counts, key=material_counts.get)
                if material_counts[top_category] > 3:
                    recommendations.append({
                        'category': 'Waste Reduction',
                        'priority': 'Medium',
                        'recommendation': f'You frequently dispose of {top_category} items. Consider reducing usage or finding reusable alternatives.',
                        'estimated_impact': 'Reduce environmental footprint by 15-25%'
                    })
        
        return recommendations
    
    def _categorize_material(self, material_name):
        """Categorize material for analysis"""
        material_lower = material_name.lower()
        
        if any(word in material_lower for word in ['plastic', 'polythene', 'styrofoam']):
            return 'plastic'
        elif any(word in material_lower for word in ['glass', 'bottle', 'jar']):
            return 'glass'
        elif any(word in material_lower for word in ['metal', 'aluminum', 'steel', 'iron']):
            return 'metal'
        elif any(word in material_lower for word in ['electronic', 'battery', 'phone', 'computer']):
            return 'electronics'
        else:
            return 'other'


class DeepLearningUsageAnalyzer:
    """Deep learning model for advanced usage pattern analysis"""
    
    def __init__(self):
        self.model = None
        self.sequence_length = 24  # 24 hours of data
        self.scaler = StandardScaler()
        
    def build_model(self, input_shape):
        """Build LSTM model for time series analysis"""
        if not TF_AVAILABLE:
            return None
            
        model = keras.Sequential([
            layers.LSTM(50, return_sequences=True, input_shape=input_shape),
            layers.Dropout(0.2),
            layers.LSTM(50, return_sequences=True),
            layers.Dropout(0.2),
            layers.LSTM(50),
            layers.Dropout(0.2),
            layers.Dense(25),
            layers.Dense(3)  # Water, electricity, gas predictions
        ])
        
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model
    
    def prepare_sequences(self, data):
        """Prepare sequential data for LSTM training"""
        if len(data) < self.sequence_length:
            return None, None
            
        features = []
        targets = []
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Create sequences
        for i in range(len(df) - self.sequence_length):
            sequence = df.iloc[i:i+self.sequence_length]
            target = df.iloc[i+self.sequence_length]
            
            # Extract features for sequence
            seq_features = []
            for _, row in sequence.iterrows():
                seq_features.append([
                    row['water_gallons'],
                    row['electricity_kwh'],
                    row['gas_cubic_m'],
                    row['timestamp'].hour,
                    row['timestamp'].dayofweek
                ])
            
            features.append(seq_features)
            targets.append([
                target['water_gallons'],
                target['electricity_kwh'],
                target['gas_cubic_m']
            ])
        
        return np.array(features), np.array(targets)
    
    def train_deep_model(self, data):
        """Train deep learning model"""
        X, y = self.prepare_sequences(data)
        
        if X is None:
            return None
            
        # Scale features
        X_reshaped = X.reshape(-1, X.shape[-1])
        X_scaled = self.scaler.fit_transform(X_reshaped)
        X_scaled = X_scaled.reshape(X.shape)
        
        # Build and train model
        self.model = self.build_model((self.sequence_length, X.shape[2]))
        
        # Split data
        split_idx = int(0.8 * len(X_scaled))
        X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Train model
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=50,
            batch_size=32,
            verbose=0
        )
        
        return history
    
    def predict_future_usage(self, recent_data):
        """Predict future usage using deep learning model"""
        if self.model is None or len(recent_data) < self.sequence_length:
            return None
            
        # Prepare recent data
        df = pd.DataFrame(recent_data[-self.sequence_length:])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        sequence = []
        for _, row in df.iterrows():
            sequence.append([
                row['water_gallons'],
                row['electricity_kwh'],
                row['gas_cubic_m'],
                row['timestamp'].hour,
                row['timestamp'].dayofweek
            ])
        
        sequence = np.array(sequence).reshape(1, self.sequence_length, -1)
        
        # Scale and predict
        sequence_reshaped = sequence.reshape(-1, sequence.shape[-1])
        sequence_scaled = self.scaler.transform(sequence_reshaped)
        sequence_scaled = sequence_scaled.reshape(sequence.shape)
        
        prediction = self.model.predict(sequence_scaled, verbose=0)
        
        return {
            'water_prediction': float(prediction[0][0]),
            'electricity_prediction': float(prediction[0][1]),
            'gas_prediction': float(prediction[0][2])
        }


# Initialize global AI components
usage_predictor = UtilityUsagePredictor()
recommendation_engine = SustainabilityRecommendationEngine()
dl_analyzer = DeepLearningUsageAnalyzer()