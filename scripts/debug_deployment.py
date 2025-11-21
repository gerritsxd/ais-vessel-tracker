
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

print(f"Project root: {project_root}")
print(f"Python executable: {sys.executable}")

try:
    print("Attempting to import src.services.web_tracker...")
    from src.services import web_tracker
    print("✓ Import successful")
    
    print(f"Frontend dist path: {web_tracker.frontend_dist}")
    if not web_tracker.frontend_dist.exists():
        print("✗ frontend_dist path does not exist!")
        print(f"  Expected: {web_tracker.frontend_dist}")
        # List contents of parent
        parent = web_tracker.frontend_dist.parent
        if parent.exists():
            print(f"  Contents of {parent}:")
            for item in parent.iterdir():
                print(f"    - {item.name}")
        else:
            print(f"  Parent {parent} does not exist")
    else:
        print("✓ frontend_dist path exists")
        
    print("Debug check passed.")
    
except ImportError as e:
    print(f"✗ ImportError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"✗ Exception during import: {e}")
    import traceback
    traceback.print_exc()
