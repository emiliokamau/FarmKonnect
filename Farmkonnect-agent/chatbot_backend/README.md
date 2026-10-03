# FarmKonnect Chatbot Backend

This folder is the complete shippable Django backend for the FarmKonnect chatbot. It includes the API, database models, migrations, and provider integration for ElevenLabs and Gemini. The chatbot UI belongs to the host application and is intentionally not included.

## Run

```powershell
cd chatbot_backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver 5100
```

Check `http://127.0.0.1:5100/api/agent/health/` to verify the backend is running.

## Database

Set `DATABASE_URL` to the same PostgreSQL database used by the host application, then run `python manage.py migrate`. The backend uses the existing database tables only after the Django migration has been applied and the model table names match.

## Provider flow

Voice requests use ElevenLabs Scribe for Swahili transcription, Gemini for Swahili-to-English translation, and ElevenLabs text-to-speech for the English reply. Keys belong in `.env`; never commit `.env`.

See [INTEGRATION.md](INTEGRATION.md) for endpoints and host-application wiring.