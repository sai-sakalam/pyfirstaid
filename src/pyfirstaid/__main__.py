import os
import sys

# `python -m pyfirstaid` puts the current folder first on sys.path, so a user's
# random.py, json.py, ... would be imported instead of the real modules that
# pyfirstaid needs. Drop it: pyfirstaid itself is already imported at this point.
_cwd = os.path.normcase(os.path.abspath(os.getcwd()))
sys.path[:] = [p for p in sys.path
               if p and os.path.normcase(os.path.abspath(p)) != _cwd]

from pyfirstaid.cli import main  # noqa: E402

sys.exit(main())
