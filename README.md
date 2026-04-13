# Backend (Django + DRF)

## Description
Backend for a psychological support platform.  
A basic user system with roles, access control, and moderation is implemented.

---

## API Documentation

The project includes built-in API documentation for convenient endpoint browsing and testing.

### Available links

- Swagger UI: `http://127.0.0.1:8000/api/v1/schema/swagger/`
- Redoc: `http://127.0.0.1:8000/api/v1/schema/redoc/`
- OpenAPI Schema: `http://127.0.0.1:8000/api/v1/schema/`

These pages allow you to:
- explore available endpoints
- check request and response schemas
- test API requests in the browser

---

## What is implemented

### Users and Roles
- custom `User` model
- roles:
  - `user`
  - `specialist`
  - `moderator`
  - `admin`
- email-based authentication (no username)
- `is_blocked` field for user blocking

### Access Control
- custom permission `IsAdminOrModerator`
- role-based access in `UserViewSet`
- only moderator/admin can:
  - change roles
  - block users
  - delete users

### Profiles
- profile management for users
- separate specialist profiles
- document management for profiles
- CRUD endpoints for profiles and specialist profiles
- document upload and deletion endpoints

### API (users)

Main endpoints:
- `GET api/v1/users/list/` — list users (admin/moderator)
- `GET api/v1/users/list/{id}/` — user details
- `POST api/v1/users/register/` — create user
- `POST api/v1/users/login/` — authorize user
- `POST api/v1/users/logout/` — logout (blacklist refresh token)
- `DELETE /users/list/{id}/` — delete user
- `POST api/v1/token/verify/` — verify token
- `POST api/v1/token/refresh/` — refresh token

Custom endpoints:
- `POST api/v1/users/list/{id}/block/` — block user
- `POST api/v1/users/list/{id}/change_role/` — change role
- `GET api/v1/users/list/me/` — current user

### API (profiles)

Profiles:
- `GET api/v1/profiles/` — list profiles
- `POST api/v1/profiles/` — create profile
- `GET api/v1/profiles/{id}/` — retrieve profile details
- `PUT api/v1/profiles/{id}/` — update profile
- `PATCH api/v1/profiles/{id}/` — partially update profile
- `DELETE api/v1/profiles/{id}/` — delete profile

Specialist profiles:
- `GET api/v1/profiles/specialists/` — list specialist profiles
- `POST api/v1/profiles/specialists/` — create specialist profile
- `GET api/v1/profiles/specialists/{id}/` — retrieve specialist profile details
- `PUT api/v1/profiles/specialists/{id}/` — update specialist profile
- `PATCH api/v1/profiles/specialists/{id}/` — partially update specialist profile
- `DELETE api/v1/profiles/specialists/{id}/` — delete specialist profile

Documents:
- `GET api/v1/profiles/documents/` — list documents
- `POST api/v1/profiles/documents/` — upload document
- `GET api/v1/profiles/documents/{id}/` — retrieve document details
- `DELETE api/v1/profiles/documents/{id}/` — delete document

---

## Authentication (JWT)

The project uses JWT authentication based on refresh and access tokens.

### Login

`POST /api/v1/users/login/`

Response:
```json
{
  "access": "access_token",
  "refresh": "refresh_token"
}
```

- `access` token is used to authenticate requests
- `refresh` token is used to obtain a new access token or to logout

---

### Logout

`POST /api/v1/users/logout/`

Headers:
```
Authorization: Bearer <access_token>
```

Body:
```json
{
  "refresh": "your_refresh_token"
}
```

### How it works

- Logout blacklists the refresh token
- After logout:
  - refresh token can no longer be used
  - access token remains valid until it expires

---

### Important

- Access token lifetime is limited (e.g. 5 minutes)
- After expiration, user must login again
- This is standard JWT behavior

---

### Security notes

- Blocked users cannot:
  - login
  - access protected endpoints
- All requests are checked with custom permissions

---

## Project structure (main parts)

```
teamproject225-backend/
├── backend/
│ ├── __init__.py
│ ├── .env.example
│ ├── config/ # Django settings, urls, asgi, wsgi
│ ├── users/
│ │ ├── api/
│ │ │ └── v1/ # API versioning
│ │ │   ├── permissions.py
│ │ │   ├── serializers.py
│ │ │   ├── urls.py
│ │ │   └── views.py
│ │ ├── migrations/
│ │ ├── admin.py # admin configuration
│ │ ├── apps.py
│ │ ├── models.py # User model
│ │ ├── selectors.py # data access layer
│ │ ├── services.py # business logic
│ │ └── __init__.py
│ ├── profiles/
│ │ ├── migrations/
│ │ ├── __init__.py
│ │ ├── admin.py
│ │ ├── apps.py
│ │ ├── models.py
│ │ ├── serializers.py
│ │ ├── urls.py
│ │ └── views.py
│ ├── manage.py
│ └── requirements.txt
├── .github/workflows/
│ ├── backend-ci.yml
│ └── python-check.yml
├── .dockerignore
├── .gitignore
├── Dockerfile
└── README.md
```

---

## How to run

Create a `.env` file in the `backend/` directory and add:
SECRET_KEY=your-secret-key

You can generate a Django secret key using:
- https://djecrety.ir/
- or via command:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

```bash
python -m venv venv
venv\Scripts\activate      # Windows

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Infrastructure & DevSecOps

The project follows modern SDLC practices with a focus on Shift Left Security. Current automation is driven by GitHub Actions workflows in [.github/workflows/](.github/workflows/).

- **CI Checks (GitHub Actions)**: The reusable workflow `python-check.yml` runs on CI calls:
  - **Linting**: `flake8` with `--max-complexity=6` (non-blocking).
  - **SAST**: `bandit` scan of the `backend/` package.
  - **Dependency Audit**: `pip-audit` against `backend/requirements.txt`.
- **Workflow Triggers**: `backend-ci.yml` runs on pushes to `main` and `develop`, PRs targeting `main`/`develop`, and manual runs (`workflow_dispatch`).
- **Container Build & Scan**: Runs only on push to `main`/`develop` or manual trigger. Docker Buildx builds the image, Trivy scans it for `CRITICAL,HIGH` issues (fails on findings, ignores unfixed), then the image is pushed to Docker Hub with `latest` and commit SHA tags.
- **CD Trigger**: After a successful image push, a `repository-dispatch` event triggers the infra repository workflow for deployment.

---

## Docker

Before running with Docker locally, make sure Docker Engine (or Docker Desktop) is installed and running on your machine.

Build image:
```bash
docker build -t teamproject225-backend:local .
```

Run container (with hot reload):

Windows (CMD):
```bat
docker run --rm -p 8000:8000 --env-file backend/.env -v "%cd%\backend:/app" teamproject225-backend:local
```

Windows (PowerShell):
```powershell
docker run --rm -p 8000:8000 --env-file backend/.env -v "${PWD}\backend:/app" teamproject225-backend:local
```

macOS/Linux:
```bash
docker run --rm -p 8000:8000 --env-file backend/.env -v "$(pwd)/backend:/app" teamproject225-backend:local
```
