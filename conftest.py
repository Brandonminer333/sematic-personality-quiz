import sys
from pathlib import Path


# Ensure repository root is importable regardless of where pytest is invoked from.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

