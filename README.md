# MiniMart

## 1. Project Overview

**MiniMart** is a real-world **Multi-tenant Shopping List Management Backend** built using **FastAPI + SQLAlchemy**.
It supports roles like **Member**, **Tenant Admin**, and **Super Admin** and provides secure, role-based APIs for managing shared shopping lists with real-time synchronization.

This project uses **`uv`** for dependency management and virtual environment handling.

## 2. Key Features

1. JWT-based authentication with OTP verification.
2. Multi-tenancy with strict data isolation (schema-based or tenant-id filters).
3. Real-time synchronization for chat and list updates using WebSockets and Redis.
4. Role-based Access Control (RBAC) at both Tenant and Shopping List levels.
5. Soft-delete support for members and shopping lists to maintain historical activity.
6. Rate limiting for API protection and bucket isolation.
7. Background task processing (Cleaning up unverified users, etc.) using Celery and Redis.

## 3. Tech Stack

* Python 3.13
* FastAPI
* SQLAlchemy (Asyncpg)
* PostgreSQL
* Redis (Rate limiting, WebSockets, Celery broker)
* Celery (Background tasks)
* JWT Authentication
* **uv** (dependency & env management)
* `pyproject.toml` + `uv.lock`

## 4. Environment Variables

Create a `.env` file based on `.env.example`:

```ini
APP_NAME=MiniMart
APP_ENV=development
DEBUG=true
SECRET_KEY=

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/minimart

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256

# Invitation Token
INVITATION_BASE_URL=

# Email Configuration
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
```

## 5. Run migrations

```bash
uv run alembic upgrade head
```

## 6. Create Admin user

```bash
uv run python scripts/create_superadmin.py
```

## 7. Start development server

```bash
uv run uvicorn app.main:app --reload
```

Application will be available at:

```
http://127.0.0.1:8000
```

## 8. API Authentication

All protected APIs require JWT access token.

```http
Authorization: Bearer <access_token>
```

## 9. Folder Structure

```bash
Minimart
.
├── app
│   ├── api           # API routers and endpoints (v1)
│   ├── common        # Shared constants and enums
│   ├── core          # Core config, dependencies, and security
│   ├── db            # Database session and naming conventions
│   ├── exceptions    # Custom HTTP exceptions
│   ├── main.py       # FastAPI application entry point
│   ├── middleware    # Request/Response middleware
│   ├── models        # SQLAlchemy data models
│   ├── schemas       # Pydantic validation schemas
│   ├── services      # Business logic layer
│   ├── tasks         # Celery background tasks
│   ├── utils         # Helper utilities (time, security)
│   └── websocket     # Real-time connection manager
├── migrations        # Alembic migration scripts
├── scripts           # Administrative scripts
├── templates         # HTML templates for testing
├── pyproject.toml    # Project dependencies and metadata
├── README.md         # This file
└── uv.lock           # Pin-tight dependency lockfile
```
