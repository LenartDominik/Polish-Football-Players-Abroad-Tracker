import sys
import os
from pathlib import Path

# Dodaj główny katalog projektu do sys.path, aby testy widziały moduł 'app'
# To pozwala na importowanie np. 'from app.backend.main import app'
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
