"""
Run ML prediction to fill in GT/DWT for vessels missing this data.
Uses patterns learned from WASP vessels.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ml.gt_dwt_predictor import predict_gt_dwt_for_all_vessels

DB_NAME = "vessel_static_data.db"

if __name__ == "__main__":
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        exit(1)
    
    print("🚀 Starting GT/DWT ML Prediction")
    print(f"📊 Database: {db_path}\n")
    
    # Predict for all vessels (or specify limit)
    import sys
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        print(f"Limiting to {limit} vessels\n")
    
    predict_gt_dwt_for_all_vessels(db_path, limit=limit)
    
    print("\n✅ Prediction complete!")

