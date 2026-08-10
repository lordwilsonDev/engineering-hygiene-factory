"""sys.path setup for the factory's own tests.

Lives in tests/ (not the repo root) so it loads under BOTH plain pytest and
mutmut — mutmut runs pytest from its mutants/ tree with rootdir there, so a
root conftest.py is outside the collected path and never loads.

Append (never prepend): under mutation runs mutmut puts mutants/scripts at
sys.path[0], so `import run_factory` must resolve to the MUTANT. Prepending
the original scripts dir here would make every mutant silently survive.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
