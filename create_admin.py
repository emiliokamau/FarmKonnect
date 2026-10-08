#!/usr/bin/env python
"""Repo-root wrapper for the real create_admin script in backend/.

Render's build runs from the repository root, where the backend package and its
settings live one level down. manage.py, asgi.py and wsgi.py already have these
wrappers; create_admin.py did not, so `python create_admin.py` failed the build
with "can't open file '/opt/render/project/src/create_admin.py'".

Mirrors manage.py: change into backend/ and drop the root from sys.path so the
farmkonnect settings module and the core_up app import correctly.
"""

import os
import runpy
import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent)
backend_dir = str(Path(__file__).resolve().parent / "backend")

os.chdir(backend_dir)
while root_dir in sys.path:
    sys.path.remove(root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farmkonnect.settings")

runpy.run_path(os.path.join(backend_dir, "create_admin.py"), run_name="__main__")
