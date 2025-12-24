"""
ML Predictor for GT and DWT
Predicts Gross Tonnage and Deadweight Tonnage based on vessel characteristics.
Trained on WASP vessel data patterns.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import pickle
import json

DB_NAME = "vessel_static_data.db"


class GTDWTPredictor:
    """Predict GT and DWT based on vessel characteristics."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.gt_model = None
        self.dwt_model = None
        self.gt_scaler = None
        self.dwt_scaler = None
        self.models_loaded = False
    
    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path, timeout=60)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    
    def load_training_data(self):
        """Load WASP vessel data for training."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get WASP vessels with complete data
            cursor.execute('''
                SELECT 
                    w.length,
                    w.dwt,
                    w.gt,
                    v.beam,
                    v.ship_type
                FROM wind_propulsion_mmsi w
                LEFT JOIN vessels_static v ON v.mmsi = w.mmsi
                WHERE w.length IS NOT NULL
                  AND w.dwt IS NOT NULL
                  AND w.gt IS NOT NULL
                  AND w.length > 0
                  AND w.dwt > 0
                  AND w.gt > 0
            ''')
            
            data = cursor.fetchall()
            
            if len(data) < 10:
                print(f"⚠️  Only {len(data)} WASP vessels with complete data. Need at least 10 for training.")
                return None, None
            
            # Prepare features and targets
            X = []  # Features: length, beam (or estimated), ship_type
            y_gt = []  # Target: GT
            y_dwt = []  # Target: DWT
            
            for length, dwt, gt, beam, ship_type in data:
                # Use beam if available, otherwise estimate from length
                if beam and beam > 0:
                    effective_beam = beam
                else:
                    # Estimate beam from length (average ratio from WASP vessels)
                    effective_beam = length / 6.59  # Average length/beam ratio from WASP vessels
                
                # Use ship_type if available, otherwise use 70 (Cargo) as default
                ship_type_code = ship_type if ship_type else 70
                
                X.append([length, effective_beam, ship_type_code])
                y_gt.append(gt)
                y_dwt.append(dwt)
            
            return np.array(X), np.array(y_gt), np.array(y_dwt)
            
        finally:
            if conn:
                conn.close()
    
    def train_models(self):
        """Train GT and DWT prediction models."""
        print("Loading training data from WASP vessels...")
        X, y_gt, y_dwt = self.load_training_data()
        
        if X is None:
            print("❌ Not enough training data")
            return False
        
        print(f"✅ Loaded {len(X)} training samples")
        
        # Scale features
        self.gt_scaler = StandardScaler()
        self.dwt_scaler = StandardScaler()
        
        X_gt_scaled = self.gt_scaler.fit_transform(X)
        X_dwt_scaled = self.dwt_scaler.fit_transform(X)
        
        # Train GT model
        print("Training GT prediction model...")
        self.gt_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.gt_model.fit(X_gt_scaled, y_gt)
        
        # Train DWT model
        print("Training DWT prediction model...")
        self.dwt_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.dwt_model.fit(X_dwt_scaled, y_dwt)
        
        # Evaluate
        gt_score = self.gt_model.score(X_gt_scaled, y_gt)
        dwt_score = self.dwt_model.score(X_dwt_scaled, y_dwt)
        
        print(f"✅ GT model R² score: {gt_score:.3f}")
        print(f"✅ DWT model R² score: {dwt_score:.3f}")
        
        self.models_loaded = True
        return True
    
    def predict_gt(self, length: float, beam: Optional[float] = None, ship_type: Optional[int] = None) -> Optional[int]:
        """Predict GT for a vessel."""
        if not self.models_loaded:
            if not self.train_models():
                return None
        
        # Prepare features
        if beam is None or beam <= 0:
            beam = length / 6.59  # Estimate from length
        
        if ship_type is None:
            ship_type = 70  # Default to Cargo
        
        X = np.array([[length, beam, ship_type]])
        X_scaled = self.gt_scaler.transform(X)
        
        prediction = self.gt_model.predict(X_scaled)[0]
        return max(100, int(prediction))  # Ensure minimum 100 GT
    
    def predict_dwt(self, length: float, beam: Optional[float] = None, ship_type: Optional[int] = None) -> Optional[int]:
        """Predict DWT for a vessel."""
        if not self.models_loaded:
            if not self.train_models():
                return None
        
        # Prepare features
        if beam is None or beam <= 0:
            beam = length / 6.59
        
        if ship_type is None:
            ship_type = 70
        
        X = np.array([[length, beam, ship_type]])
        X_scaled = self.dwt_scaler.transform(X)
        
        prediction = self.dwt_model.predict(X_scaled)[0]
        return max(100, int(prediction))  # Ensure minimum 100 DWT
    
    def predict_for_vessel(self, mmsi: int) -> Tuple[Optional[int], Optional[int]]:
        """Predict GT and DWT for a vessel by MMSI."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT length, beam, ship_type
                FROM vessels_static
                WHERE mmsi = ?
            ''', (mmsi,))
            
            row = cursor.fetchone()
            if not row:
                return None, None
            
            length, beam, ship_type = row
            
            if not length or length <= 0:
                return None, None
            
            gt = self.predict_gt(length, beam, ship_type)
            dwt = self.predict_dwt(length, beam, ship_type)
            
            return gt, dwt
            
        finally:
            if conn:
                conn.close()


def predict_gt_dwt_for_all_vessels(db_path, limit=None):
    """Predict GT/DWT for all vessels missing this data."""
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=60)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        # Get vessels missing GT or DWT
        query = '''
            SELECT mmsi, length, beam, ship_type
            FROM vessels_static
            WHERE mmsi IS NOT NULL
              AND length IS NOT NULL
              AND length > 0
              AND (gt IS NULL OR gt = 0 OR dwt IS NULL OR dwt = 0)
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query)
        vessels = cursor.fetchall()
        
        print(f"Found {len(vessels)} vessels needing GT/DWT prediction")
        
        predictor = GTDWTPredictor(db_path)
        
        updated_count = 0
        
        for mmsi, length, beam, ship_type in vessels:
            gt, dwt = predictor.predict_for_vessel(mmsi)
            
            if gt or dwt:
                # Update database
                updates = []
                values = []
                
                if gt:
                    updates.append('gt = ?')
                    updates.append('gt_source = ?')
                    updates.append('gt_updated_at = datetime("now")')
                    values.extend([gt, 'predicted'])
                
                if dwt:
                    updates.append('dwt = ?')
                    updates.append('dwt_source = ?')
                    updates.append('dwt_updated_at = datetime("now")')
                    values.extend([dwt, 'predicted'])
                
                values.append(mmsi)
                
                cursor.execute(f'''
                    UPDATE vessels_static
                    SET {', '.join(updates)}
                    WHERE mmsi = ?
                ''', values)
                
                updated_count += 1
        
        conn.commit()
        print(f"✅ Updated {updated_count} vessels with predicted GT/DWT")
        
    finally:
        if conn:
            conn.close()


def main():
    """Main function."""
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print("="*80)
    print("GT/DWT ML PREDICTION")
    print("="*80)
    print()
    
    # Predict for all vessels (or limit to 1000 for testing)
    predict_gt_dwt_for_all_vessels(db_path, limit=1000)
    
    print()
    print("✅ Prediction complete!")


if __name__ == "__main__":
    main()

