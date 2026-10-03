# Integration Guide

The host application can live in a different folder, repository, or server. It owns the chatbot UI and calls this backend over HTTP. This package does not serve a chatbot interface.

## Base URL

Local development:

```text
http://127.0.0.1:5100
```

Set `CORS_ALLOWED_ORIGINS` to the host application's frontend origin.

## Data access

Use one aggregate request when the chatbot needs the complete farmer context:

```http
GET /api/farmers/{farmer_id}/data/
```

The response includes `farmer`, `farms`, nested `crops`, `disease_reports`, `harvests`, `inventory`, `recent_sales`, `conversations`, and `agent_actions`.

The individual resources are also available:

```text
/api/farmers/
/api/farms/
/api/crops/
/api/planting-activities/
/api/disease-reports/
/api/harvests/
/api/inventory/
/api/sales/
/api/conversations/
/api/agent-actions/
```

Use `GET` for host-application reads. Write methods are available on the resource routes for development, but should be protected and restricted before production deployment.

## Text conversation

```http
POST /api/agent/respond/
Content-Type: application/json
```

```json
{"farmer_id":"FARMER_UUID","message":"Nimeuza gunia tano leo"}
```

The backend classifies the message, fetches farmer context, records a conversation and agent action, and returns the response JSON.

## Voice conversation

```http
POST /api/agent/respond-audio/
Content-Type: multipart/form-data
```

Fields:

```text
farmer_id: FARMER_UUID
audio: recorded audio file
```

The response includes `transcript`, `translation`, `audio_base64`, and `audio_content_type`.

## Health check

```http
GET /api/agent/health/
```

Use this endpoint before enabling the host application's chatbot toggle.