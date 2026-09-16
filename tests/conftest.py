import sys
from pathlib import Path

# Make the project root (where app.py lives) importable regardless of
# where pytest is invoked from, since tests/ has no __init__.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
