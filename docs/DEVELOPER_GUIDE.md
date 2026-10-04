# FarmKonnect Developer Guide

FarmKonnect is an all-in-one agricultural information and services platform built with Django, Django REST Framework, and a native HTML, CSS, and JavaScript frontend. It brings county and commodity market prices, agricultural events and grants, post-harvest advisory requests, Point of Sale (POS), and Farm Management (FMS) into a single unified application.

This guide documents the repository as configured for local development.

## 1. System Architecture & Overview

### High-level architecture

```text
Browser (HTML5 / CSS3 / ES6 Fetch)
  |
  +---> https://farmkonnect.zirocreativeagency.co.ke/ (index.html, login.html, dashboard.html, pos.html, etc.)
  |
  +---> https://farmkonnect.zirocreativeagency.co.ke/api/ (Django REST Framework endpoints)
          |
          v
      Django URL router -> Django REST Framework viewsets
          |
          v
      Database (PostgreSQL production / SQLite local) + Django models
          +-- User & Farmer Profile
          +-- Market prices & County/Commodity reference data
          +-- Farm Management (Farms, Crops, Plantings, Inputs, Diseases, Harvests, Inventory)
          +-- Point of Sale & Marketplace (Products, Listings, Orders)
          +-- Advisory Requests & Events
```

The frontend uses standard HTML5, CSS3, and JavaScript located in `frontend/`, served in production via Nginx reverse proxy.
API calls are performed using `frontend/js/api.js` with the relative base URL `/api/` and Token authentication.

### Implemented frontend areas

- **Welcome page:** `https://farmkonnect.zirocreativeagency.co.ke/` or `index.html` displays the FarmKonnect portal landing page with dynamic service cards.
- **Login & Registration:** `login.html`, `register.html`, and `verify-otp.html` handle user registration, phone/email password verification, and 6-digit OTP verification.
- **Farmer Profile Setup:** `farmer-profile.html` allows farmers to save their details and location.
- **Dashboard:** `dashboard.html` provides the main hub for overview metrics and Farm Management System (FMS).
- **Point of Sale (POS):** `pos.html` provides sales, product catalogs, customer tracking, and reports.
- **Farmer Portal:** `farmer-portal.html` provides price comparison, market trends, AI disease diagnosis, best practices, and officer communication.

### User roles & Authentication

The repository defines a custom user model `backend.User` supporting phone and email login with OTP verification:
- Default authentication: Token authentication (`Token <key>` header)
- Anonymous users can view reference data (commodities, counties, prices, events, published products).
- Authenticated farmers and extension officers can manage farms, crops, sales, and advisory requests.

## 2. Local Development Setup

### Prerequisites

- Windows, macOS, or Linux
- Python 3.11+
- Git

### Running on Localhost

#### Option A: One-click Start Script (PowerShell / Windows)
From the repository root:

```powershell
.\start.ps1
```

Or for Command Prompt:

```cmd
start.bat
```

#### Option B: Manual Setup
From the repository root:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver 127.0.0.1:8000
```

The application is then live at `http://127.0.0.1:8000/`.

### Default Accounts
- **Admin / Demo Account:**
  - Phone: `0701519479`
  - Password: `Admin1234`
  - OTP in development: Printed in terminal / console output and returned in login API response for rapid testing.


## 3. Environment Variables

The backend reads these variables from the process environment:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-development-value
DJANGO_DEBUG=True
MARKET_PRICE_API_URL=https://api.example.com/price
MARKET_PRICE_API_KEY=replace-with-market-data-key
AI_ADVISORY_ENDPOINT=https://api.openai.com/v1/completions
AI_ADVISORY_KEY=replace-with-ai-provider-key
AI_MODEL=gpt-4o-mini
```

| Variable | Required | Description |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | No for local development | Django signing and cryptographic key. The code has an insecure development fallback, so set a private value outside local throwaway work. |
| `DJANGO_DEBUG` | No | The code treats the exact value `True` as enabled. Use `False` for a non-debug environment. |
| `MARKET_PRICE_API_URL` | No | URL used by the service layer when fetching external market prices. The code defaults to an example URL. |
| `MARKET_PRICE_API_KEY` | No | Optional bearer credential sent to the market-price provider. |
| `AI_ADVISORY_ENDPOINT` | No | URL used by the advisory service to request an AI recommendation. The code defaults to an OpenAI-compatible completions URL. |
| `AI_ADVISORY_KEY` | Required to call the configured AI provider | Bearer credential for the advisory provider. |
| `AI_MODEL` | No | Model name sent in the advisory request. Defaults to `gpt-4o-mini`. |

There are currently no database URI, JWT secret, FCM key, or frontend API URL variables read by the repository. The database is SQLite and the frontend API URL is currently hard-coded.

For PowerShell, set variables for the current terminal session with:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-development-value"
$env:DJANGO_DEBUG = "True"
```

Do not commit real secrets. The repository `.gitignore` excludes `.env` files and common local secret files.

## 4. Backend & API Integration Guide

### Base URL and authentication

The API base URL is:

```text
https://farmkonnect.zirocreativeagency.co.ke/api/
```

DRF is configured with:

- Django `SessionAuthentication`
- HTTP Basic Authentication
- A default `IsAuthenticated` permission

The project does not currently configure JWT or Bearer-token authentication. Frontend requests use Axios with `withCredentials: true`, but the frontend does not yet include a login flow or an explicit Basic Auth header.

### Request and response conventions

- Successful list endpoints return a JSON array.
- Successful detail and create/update endpoints return a JSON object.
- The backend uses DRF validation responses, normally shaped as an object keyed by field name.
- General errors use a `detail` field, for example `{"detail":"commodity and county are required"}`.
- Dates use ISO date strings such as `2026-10-03`.
- Related commodities and counties are represented by slug values (`commodity` code and `county` name) in price and advisory payloads.
- Related objects such as users, products, listings, and buyers are represented by numeric primary keys.

### Example: market-price trend

```http
GET /api/prices/trend/?commodity=MAIZE&county=Nairobi&days=30
```

Authentication is required. The service returns the trend data produced by `get_price_trend`:

```json
[
  {
    "date": "2026-10-03",
    "wholesale": "52.00",
    "retail": "68.00"
  }
]
```

When either required query parameter is missing:

```json
{
  "detail": "commodity and county are required"
}
```

### Example: create an advisory request

```http
POST /api/advisories/
Content-Type: application/json
```

```json
{
  "commodity": "MAIZE",
  "quantity": "250.00",
  "harvest_date": "2026-10-03",
  "storage_option": "immediate"
}
```

The view assigns the authenticated user as `farmer`. A successful response includes the created resource, for example:

```json
{
  "id": 1,
  "farmer": 7,
  "commodity": "MAIZE",
  "quantity": "250.00",
  "harvest_date": "2026-10-03",
  "storage_option": "immediate",
  "created_at": "2026-10-03T12:00:00Z",
  "recommendation": null,
  "price_snapshot": null
}
```

### Example: run an advisory

```http
POST /api/advisories/1/run/
```

Successful processing returns:

```json
{
  "detail": "Advisory generated."
}
```

The frontend then reads the generated recommendation with:

```http
GET /api/advisories/1/
```

If the request already has a recommendation, the run action returns HTTP 400:

```json
{
  "detail": "Advisory already processed."
}
```

### Available router resources

The URL configuration registers these resources below `/api/`:

```text
prices_csv/
products/
listings/
orders/
device_tokens/
users/
counties/
commodities/
prices/
prices/trend/
events/
advisories/
advisories/{id}/run/
```

The standard DRF list, detail, create, update, and delete actions are only available where the corresponding viewset is a `ModelViewSet`; users, counties, commodities, prices, and events are read-only viewsets.

## 5. Database Schema Overview

The models are defined in `backend/models.py` and use Django ORM relationships:

| Model | Key fields and relationships |
| --- | --- |
| `User` | Declared as an extension of Django's `AbstractUser`; adds `role` with `farmer`, `officer`, and `admin`. `AUTH_USER_MODEL` is not currently set in project settings, so verify the active user model before integrating authentication. |
| `County` | Unique county name. A county has many market prices and can belong to many events. |
| `Commodity` | Unique commodity code and name. A commodity has many market prices and advisory requests. |
| `MarketPrice` | Belongs to one commodity and one county. The combination of commodity, county, and date is unique. |
| `Event` | Training or grant event; has a many-to-many relationship with counties. |
| `AdvisoryRequest` | Belongs to one farmer and one commodity; stores quantity, harvest date, storage option, recommendation, and an optional JSON price snapshot. |
| `Product` | Marketplace product owned by a vendor (`User`). |
| `Listing` | Belongs to a product and stores available quantity, unit price, and active state. |
| `Order` | Belongs to a buyer and a listing; stores quantity, calculated total price, and status. |
| `DeviceToken` | Stores one unique notification token for a user and platform. |

Relationship summary:

```text
User 1 --- * Product 1 --- * Listing 1 --- * Order * --- 1 User (buyer)
User 1 --- * AdvisoryRequest * --- 1 Commodity 1 --- * MarketPrice * --- 1 County
Event * --- * County
User 1 --- * DeviceToken
```

`Order.total_price` is calculated on save when it is not provided, using `quantity * listing.unit_price`. Deleting a commodity cascades to its market prices but is protected when advisory requests reference it. Listings are protected from deletion while orders reference them.

## 6. Contribution Guidelines

### Branching and commits

Use a short-lived branch based on the current default branch:

```text
feature/short-description
fix/short-description
docs/short-description
```

Keep commits focused and use imperative messages, for example:

```text
Add market price trend filters
Document local development setup
Fix advisory request validation
```

The repository currently has `master` checked out locally while the GitHub repository metadata identifies `main` as the default branch. Confirm the target branch before opening a pull request.

### Backend practices

- Follow Django and DRF conventions already used by the project.
- Keep serializers focused on API shape and validation; keep business logic in services or viewset actions.
- Use `python manage.py check` and the relevant test command before submitting changes.
- Add or update migrations when changing Django models.
- Do not commit SQLite databases, secrets, virtual environments, or generated static/media files.

### Frontend practices

- Keep API access in `frontend/js/api.js`.
- Use native HTML5, CSS3, and modern JavaScript (ES6+).
- All static assets (CSS, JS, images) are served directly by Django.

### Validation checklist

```powershell
cd backend
python manage.py check
python manage.py test tests
```

