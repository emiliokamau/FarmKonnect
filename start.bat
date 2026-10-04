@echo off
setlocal
echo ========================================
echo    Starting FarmKonnect on Localhost   
echo ========================================

cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Checking dependencies...
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet

echo Running database migrations...
venv\Scripts\python.exe manage.py migrate --noinput

echo Seeding initial reference data...
venv\Scripts\python.exe manage.py seed_data

echo.
echo FarmKonnect is running at http://127.0.0.1:8000/
echo Default login: 0701519479 / Admin1234
echo.

venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
