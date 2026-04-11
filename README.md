# Backend (Django + DRF)

## Description
Backend for a psychological support platform.  
A basic user system with roles, access control, and moderation is implemented.

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
backend/
├── config/ # Django settings, urls, asgi, wsgi
├── users/
│ ├── api/
│ │ └── v1/ # API versioning
│ │ ├── permissions.py
│ │ ├── serializers.py
│ │ ├── urls.py
│ │ └── views.py
│ ├── migrations/
│ ├── admin.py # admin configuration
│ ├── apps.py
│ ├── models.py # User model
│ ├── selectors.py # data access layer
│ ├── services.py # business logic
│ └── __init__.py
├── .gitignore
├── manage.py
└── requirements.txt
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
