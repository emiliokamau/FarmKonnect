#!/usr/bin/env python
import os
import sys
from pathlib import Path

# Change working directory to backend and remove root from sys.path to prevent namespace collision
root_dir = str(Path(__file__).resolve().parent)
backend_dir = str(Path(__file__).resolve().parent / "backend")
os.chdir(backend_dir)

while root_dir in sys.path:
    sys.path.remove(root_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmkonnect.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
