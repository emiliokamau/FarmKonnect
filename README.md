# FarmKonnect

FarmKonnect is an all-in-one agricultural information and services platform built with Django, Django REST Framework, and a responsive HTML, CSS, and JavaScript frontend. It provides real-time market prices, plant disease detection, point of sale (POS), farm management (FMS), agricultural events, subsidy programs, and advisory services.

## Architecture

The entire platform runs seamlessly on Django serving both the REST API and the frontend pages:
- **Backend:** Django 5.1 + Django REST Framework + SQLite + Token Authentication
- **Frontend:** HTML5, CSS3, and JavaScript (ES6+ with Fetch API)
- **Local Host URL:** `http://localhost:8000/` or `http://127.0.0.1:8000/`

## Quick Start (Run on Localhost)

### 1. Prerequisites
- Python 3.11+
- Virtual environment support

### 2. Start the Application
From the repository root in PowerShell:

```powershell
.\start.ps1
```

Or manually:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver 127.0.0.1:8000
```

### 3. Access the Application
Open your browser and navigate to:
- **Web App:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Dashboard:** [http://127.0.0.1:8000/dashboard.html](http://127.0.0.1:8000/dashboard.html)
- **Point of Sale (POS):** [http://127.0.0.1:8000/pos.html](http://127.0.0.1:8000/pos.html)
- **Farmer Portal:** [http://127.0.0.1:8000/farmer-portal.html](http://127.0.0.1:8000/farmer-portal.html)
- **Login / Register:** [http://127.0.0.1:8000/login.html](http://127.0.0.1:8000/login.html)
- **Django Admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- **API Root:** [http://127.0.0.1:8000/api/](http://127.0.0.1:8000/api/)

### Default Demo / Superuser Credentials
- **Username / Phone:** `farmconnect` / `0701519479`
- **Password:** `Admin1234`
- **OTP for local testing:** Generated in terminal output and returned in login API response for instant verification.

## Project Structure
```text
backend/
  backend/           # Core Django app: models, views, serializers, migrations, admin
  farmkonnect/       # Django project configuration (settings.py, urls.py, wsgi.py)
  market_data/       # Market data CSV cache
  tests/             # Automated test suite
  manage.py          # Django CLI
  requirements.txt   # Python dependencies
frontend/
  css/style.css      # Core styles
  js/                # Frontend API client and page logic
  *.html             # HTML pages (index, login, dashboard, pos, farmer-portal, etc.)
docs/                # Developer guides and documentation
start.ps1            # One-click localhost runner script
```
