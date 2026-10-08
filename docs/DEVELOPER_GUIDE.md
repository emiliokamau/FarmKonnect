# FarmKonnect Developer Guide

FarmKonnect is a Django REST Framework portal with HTML, CSS, and vanilla JavaScript pages for agricultural information and services. It brings county and commodity market prices, agricultural events and grants, post-harvest advisory requests, and a marketplace data model into one application for farmers and agricultural extension teams.

This guide documents the repository as it exists today. It does not describe planned features or infrastructure that is not present in the codebase.

## 1. System Architecture & Overview

### High-level architecture

```text
Browser
  |
  | HTML/CSS/JavaScript UI
  v
http://localhost:8000/api/
  |
  | Django URL router -> Django REST Framework viewsets
  v
SQLite database + Django models
  |
  +-- market price and event data
  +-- advisory request and recommendation data
  +-- marketplace and device-token data
```

The frontend consists of Django-served HTML pages in `frontend/`, with CSS in `frontend/css/` and browser JavaScript in `frontend/js/`. API requests are made by the page scripts to `http://localhost:8000/api/`.

The backend is a Django project in `backend/`. API routes are mounted below `/api/` with a Django REST Framework router. The local database configuration uses SQLite at `backend/db.sqlite3`.

There is no Docker configuration, CI workflow, Render configuration, Vercel configuration, or other deployment definition in this repository.

### Implemented frontend areas

- **Welcome page:** the root route displays `frontend/index.html`.
- **Farmer portal:** `frontend/farmer-portal.html` provides the farmer-facing portal.
- **Dashboard and POS:** `frontend/dashboard.html` and `frontend/pos.html` provide the authenticated application pages.
- **Authentication pages:** login, registration, and OTP verification pages are served as standalone HTML files.

### User roles

The repository declares a `backend.User` model with these roles:

| Role | Intended responsibility | Implemented access behavior |
| --- | --- | --- |
| `farmer` | Submit and view their own advisory requests; use farmer-facing portal features. | Advisory querysets are limited to the authenticated farmer. |
| `officer` | County-level agricultural extension work and access to advisory outcomes. | Officers can access the advisory queryset. |
| `admin` | Platform administration. | The role is defined in the model; Django admin permissions still apply separately. |

All configured DRF endpoints use authentication by default. Most read-only reference endpoints explicitly require `IsAuthenticated`. Advisory endpoints add role-aware permissions. Note that `farmkonnect/settings.py` does not currently set `AUTH_USER_MODEL = "backend.User"`; verify and correct that configuration before relying on the custom role field in a new environment.

## 2. Local Development Setup

### Prerequisites

- Windows, macOS, or Linux
- Python compatible with Django 5.1
- Git
- A local SQLite installation is not required separately because Python includes SQLite support.

The repository currently declares these backend packages in `backend/requirements.txt`:

```text
django==5.1
djangorestframework==3.15.2
django-filter==24.3
celery==5.4.0
requests==2.32.3
```

The frontend has no Node.js dependency installation step. Its HTML, CSS, and vanilla JavaScript assets are served directly by Django.

### Backend installation

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run Django checks and initialize the database:

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

Start the backend:

```powershell
python manage.py runserver 8000
```

The backend is then available at `http://localhost:8000/`, with the API at `http://localhost:8000/api/` and the admin site at `http://localhost:8000/admin/`.

### Current setup blockers

The repository needs these code corrections before a clean first run:

1. `backend/farmkonnect/urls.py` registers `ProductViewSet`, `ListingViewSet`, `OrderViewSet`, and `DeviceTokenViewSet` without importing them from `backend.views`.
2. The repository has no committed Django migration files. Run `makemigrations` after the backend imports are corrected.
3. Authentication endpoints are not implemented in the current router. A user must therefore be created through Django admin, the Django shell, or another existing provisioning process before authenticated API calls can be made.

These are repository facts, not additional features to implement as part of this documentation.

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

The local base URL is:

```text
http://localhost:8000/api/
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

### Crop and disease photo uploads

Farmers photograph crops and diseased plants from a phone, so the crop and
disease endpoints accept `multipart/form-data` as well as JSON. Uploaded files
are stored under `MEDIA_ROOT` (`backend/media/`) and served from `/media/`.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/crops/` | Crop record with one optional `image` file, or a `photo_url` link. |
| `POST /api/diseases/` | Disease report with a main `image` plus any extra angles as repeated `images` fields. |
| `POST /api/diseases/{id}/add_photos/` | Attach up to 5 further angles to an existing report. |
| `DELETE /api/diseases/{id}/photos/{photo_id}/` | Remove one extra photo. |
| `POST /api/diseases/{id}/analyse/` | Flag a report as awaiting a diagnosis. |
| `GET /api/diseases/pending/` | Reports with no diagnosis yet (officer/analyst view). |
| `GET /api/disease-photos/` | Extra photos across the farmer's reports. |

Uploading a report with several photos in one request:

```http
POST /api/diseases/
Content-Type: multipart/form-data; boundary=...
Authorization: Token <token>

date=2026-10-08
crop=Maize
variety=SC651
growth_stage=flowering
symptoms=yellow spots on lower leaves
affected_area=about a quarter of the field
photo_stage=leaf
needs_analysis=true
image=@main.jpg
images=@whole-plant.jpg
images=@field.jpg
```

The first `image` becomes the report's main photo; the repeated `images` fields
become `DiseasePhoto` rows. `photo_stage` and `caption` are positional and match
the order of the extra files. Responses include ready-to-use URLs so the
frontend never has to build them:

```json
{
  "id": 7,
  "image_src": "http://127.0.0.1:8000/media/diseases/2026/10/main.jpg",
  "photos": [
    {"id": 16, "image_src": "http://127.0.0.1:8000/media/diseases/2026/10/whole-plant.jpg",
     "photo_stage": "whole_plant"}
  ],
  "photo_count": 3
}
```

Validation rules:

- Photos must be JPEG, PNG or WebP and no larger than **6 MB** each; a report
  holds one main photo plus at most **5** extra angles.
- A report with `needs_analysis=true` must include at least one photo, so nothing
  can be queued for review without evidence.
- `photo_url` still works for externally hosted images and passes through
  unchanged, alongside the uploaded-file path.

The browser resizes large phone photos to roughly 3 MB before upload
(`frontend/js/image-picker.js`), which matters on slow rural connections; the
6 MB server limit is the backstop. In production, serve `MEDIA_ROOT` from the web
server or object storage rather than Django, and set the storage backend in
`settings.py` if uploads should go to S3-compatible storage.

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

- Keep API access in the relevant page script under `frontend/js/`.
- Preserve the existing HTML and CSS structure when updating the standalone pages.
- Handle API errors visibly in the page UI where possible.

### Validation checklist

```powershell
cd backend
python manage.py check
python manage.py test

cd ..\frontend
npm test -- --watchAll=false
npm run build
```

The commands above are the intended validation workflow. They may remain blocked until the missing frontend dependency, missing URL imports, and migration baseline are corrected.
