# FarmKonnect

FarmKonnect is an enterprise agricultural information and services platform built with Django, Django REST Framework, and a modern responsive HTML, CSS, and JavaScript frontend. It provides real-time market prices, plant disease detection, point of sale (POS), farm management (FMS), agricultural events, subsidy programs, advisory services, and the KonnectAI voice-and-text assistant.

---

## Production Endpoints

- **Live Platform:** [https://farmkonnect.zirocreativeagency.co.ke/](https://farmkonnect.zirocreativeagency.co.ke/)
- **Dashboard (FMS):** [https://farmkonnect.zirocreativeagency.co.ke/dashboard.html](https://farmkonnect.zirocreativeagency.co.ke/dashboard.html)
- **Point of Sale (POS):** [https://farmkonnect.zirocreativeagency.co.ke/pos.html](https://farmkonnect.zirocreativeagency.co.ke/pos.html)
- **Farmer Portal:** [https://farmkonnect.zirocreativeagency.co.ke/farmer-portal.html](https://farmkonnect.zirocreativeagency.co.ke/farmer-portal.html)
- **Events:** [https://farmkonnect.zirocreativeagency.co.ke/events.html](https://farmkonnect.zirocreativeagency.co.ke/events.html)
- **API Root:** [https://farmkonnect.zirocreativeagency.co.ke/api/](https://farmkonnect.zirocreativeagency.co.ke/api/)
- **Admin Panel:** [https://farmkonnect.zirocreativeagency.co.ke/admin/](https://farmkonnect.zirocreativeagency.co.ke/admin/)
- **WebSocket Endpoint:** `wss://farmkonnect.zirocreativeagency.co.ke/ws/konnect-ai/`

---

## Architecture

- **Backend:** Django 5.1 + Django REST Framework + Channels 4.3 + PostgreSQL (Production)
- **ASGI Server:** Daphne / Gunicorn + Uvicorn reverse-proxied behind Nginx with Let's Encrypt TLS
- **Frontend:** Pure HTML5, CSS3, and ES6 JavaScript (Fetch API + WebSockets)
- **Voice & AI:** Google Gemini 1.5 + ElevenLabs STT/TTS + TextSMS Kenya Gateway

### Repository layout

```text
backend/    Django project, core_up app, konnect_ai app, serializers, viewsets, services, and tests
frontend/   Django-served HTML pages, CSS, and vanilla JavaScript
docs/       Developer documentation
deploy/     Nginx, systemd, and provisioning manifests
```

---

## Deployment & Production Setup

The complete production deployment manifests are located in the `deploy/` directory:
- `deploy/nginx/farmkonnect.conf`: Nginx reverse proxy configuration with TLSv1.3, HSTS, and WebSocket support.
- `deploy/systemd/farmkonnect.service`: Systemd service unit for the Daphne ASGI daemon.
- `deploy/setup.sh`: One-click deployment script for Ubuntu 22.04 / 24.04 LTS servers.
- `deploy/rotate_credentials.py`: Cryptographic key and credential rotation utility.
- `deploy/backup.sh`: Atomic point-in-time snapshot and rollback script.

To deploy on a server:
```bash
sudo bash deploy/setup.sh
```

---

## Local Development (Optional)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

## Automated Test Suite

```powershell
cd backend
python manage.py test
```
