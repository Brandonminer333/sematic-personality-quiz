import sys
from pathlib import Path


# Ensure the repository root is on sys.path regardless of where pytest is
# invoked from, so `import api.api` and `import api.classifier` resolve.
# We also keep `data_sythesizer` directly importable for the offline
# data-generation tests that historically lived under `backend/`.
_ROOT = Path(__file__).resolve().parent
for _entry in (_ROOT, _ROOT / "data_sythesizer"):
    s = str(_entry)
    if s not in sys.path:
        sys.path.insert(0, s)
