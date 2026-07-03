"""Make the src/ layout importable during tests without an editable install.

The package lives under src/quality_gate, which isn't on sys.path by default.
pytest loads this root conftest before collecting tests, so inserting src/ here
guarantees `import quality_gate` works in the weekend build. (For a production
setup you'd instead `pip install -e .` with a build backend.)
"""

import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
