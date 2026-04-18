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

## OAuth (Google Login)

### What is implemented

Google OAuth authentication is implemented using:
- django-allauth
- dj-rest-auth
- JWT (SimpleJWT)

Custom logic:
- Blocking login for users with `is_blocked=True`
- Auto-connecting existing users by email
- JWT tokens returned after Google login

---

## Google Console Setup

1. Go to Google Cloud Console
2. Create project
3. Enable:
   - Google People API
   - OAuth2

4. Create OAuth Client ID:
   - Type: Web application

### Authorized redirect URIs (IMPORTANT)

For development (React):
```
http://localhost:5173/auth/google/callback
```

For backend-only testing:
```
http://127.0.0.1:8000/accounts/google/login/callback/
```

---

## Django Settings

Already configured:

- SITE_ID = 1
- REST_USE_JWT = True
- JWT enabled
- allauth + google provider

See settings:

(see settings.py)


---

## Google Login Endpoint

### Endpoint

POST:
```
/api/v1/users/google/
```

### Request

```json
{
  "access_token": "your_google_access_token"
}
```

### Response

```json
{
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "first_name": "Name",
    "last_name": "Surname"
  },
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token"
}
```

---

## Flow (React + Backend)

1. React → Google OAuth
2. Google → redirect to:
```
http://localhost:5173/auth/google/callback
```

3. React extracts `access_token`
4. React sends POST to backend:
```
/api/v1/users/google/
```

5. Backend:
- verifies token via Google
- creates / gets user
- returns JWT tokens

6. React:
- stores token
- sends Authorization header

---

## Blocking users

- Implemented via `is_blocked`
- Applied in:
  - JWT login
  - Google OAuth
  - Permissions

Blocked user:
- cannot login
- cannot access endpoints

---

## Notes

- Callback URL must match Google Console exactly
- React must be running for frontend callback
- Backend-only flow uses `/accounts/google/login/`

---

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
- `DELETE api/v1/profiles/documents/{id}/` — delete a document

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
  - an access token remains valid until it expires

---

### Important

- Access token lifetime is limited (e.g. 5 minutes)
- After expiration, the user must log in again
- This is standard JWT behavior

---

### Security notes

- Blocked users cannot:
  - login
  - access protected endpoints
- All requests are checked with custom permissions
- The minimum password length is 8 characters, and the maximum is 128

---

## Project structure (main parts)

```
teamproject225-backend/
├── .github/workflows/
│ ├── backend-ci.yml
│ └── python-check.yml
├── backend/
│ ├── __init__.py
│ ├── .env.example
│ ├── config/ # Django settings, urls, asgi, wsgi
│ ├── users/
│ │ ├── api/
│ │ │ └── v1/ # API versioning
│ │ │   ├── permissions.py
│ │ │   ├── serializers.py
│ │ │   ├── validators.py
│ │ │   ├── urls.py
│ │ │   └── views.py
│ │ ├── migrations/
│ │ ├── __init__.py
│ │ ├── admin.py # admin configuration
│ │ ├── apps.py
│ │ ├── models.py # User model
│ │ ├── selectors.py # data access layer
│ │ ├── services.py # business logic
│ │ └── social_adapter.py # OAuth logic
│ ├── profiles/
│ │ ├── migrations/
│ │ ├── __init__.py
│ │ ├── admin.py
│ │ ├── apps.py
│ │ ├── models.py
│ │ ├── serializers.py
│ │ ├── urls.py
│ │ └── views.py
│ ├── __init__.py
│ ├── manage.py
│ ├── .env.example
│ └── requirements.txt
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

---

## 🔄 Updates (Registration, Profiles, Documents)

### Registration

During registration (`POST api/v1/users/register/`), user must choose a role:

Available roles:
- `user`
- `specialist`

Other roles (`moderator`, `admin`) cannot be assigned during registration.

Example request:
```json
{
  "email": "user@example.com",
  "password": "StrongPassword123",
  "role": "specialist"
}
```

---

### Registration flow

#### If role = `user`
1. Register
2. Create profile:
   POST `/api/v1/profiles/`

#### If role = `specialist`
1. Register
2. Create specialist profile:
   POST `/api/v1/profiles/specialists/`
3. Upload documents:
   POST `/api/v1/profiles/documents/`

---

### Profiles changes

- `user` field is no longer selectable in API forms
- It is automatically assigned using authenticated user:
```python
serializer.save(user=request.user)
```

- In responses, user is shown as email:
```python
user_email = serializers.EmailField(source="user.email", read_only=True)
```

---

### Documents changes

- `specialist` field is no longer selectable
- It is automatically assigned:
```python
serializer.save(specialist=user.specialist_profile)
```

- Displayed as email:
```python
specialist = serializers.EmailField(source="specialist.user.email", read_only=True)
```

---

### Document upload rules

- Only users with role `specialist` can upload documents
- Specialist must have a profile before uploading documents

---

### Security improvements

- Cannot create profile for another user
- Cannot assign document to another specialist
- Ownership is enforced via `request.user`
- Related fields are read-only
