import os
import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent)
backend_dir = str(Path(__file__).resolve().parent / "backend")
os.chdir(backend_dir)
while root_dir in sys.path:
    sys.path.remove(root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from farmkonnect.wsgi import application
