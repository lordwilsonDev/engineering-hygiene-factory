"""sys.path setup for the factory's own tests.

Lives in tests/ (not the repo root) so it loads under BOTH plain pytest and
mutmut — mutmut runs pytest from its mutants/ tree with rootdir there, so a
root conftest.py is outside the collected path and never loads.

Append (never prepend): under mutation runs mutmut puts mutants/scripts at
sys.path[0], so `import run_factory` must resolve to the MUTANT. Prepending
the original scripts dir here would make every mutant silently survive.

Also points semantic checkpoints at a session temp dir (cleaned at exit): the
versioned checkpoints/ store is durable ledger history, so tests that invoke
status_report.main() (e.g. the mutation-closure suite) must never pollute it.
"""

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))

_checkpoint_tmp = Path(tempfile.mkdtemp(prefix="semantic-checkpoints-test-"))
os.environ.setdefault("SEMANTIC_CHECKPOINT_DIR", str(_checkpoint_tmp))
atexit.register(lambda: shutil.rmtree(_checkpoint_tmp, ignore_errors=True))
