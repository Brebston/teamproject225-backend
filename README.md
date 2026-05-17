# Backend (Django + DRF)

Backend for a psychological support platform.

The project includes:
- custom user model with email authentication
- role-based access control
- user blocking and moderation
- JWT authentication
- Google OAuth login
- password reset via Celery and Redis
- user and specialist profiles
- document uploads
- media file support
- Events app with categories, images, likes, comments, and comment likes
- Scheduling app with slots & appointments
- built-in OpenAPI documentation

---

## Table of Contents

- [API Documentation](#api-documentation)
- [Authentication](#authentication)
- [Users and Roles](#users-and-roles)
- [Profiles and Documents](#profiles-and-documents)
- [Events App](#events-app)
- [Scheduling App](#scheduling-app)
- [Education Materials App](#education-materials-app)
- [Password Reset](#password-reset-django--drf--celery)
- [Google OAuth Login](#google-oauth-login)
- [Media Support](#media-support)
- [Project Structure](#project-structure-main-parts)
- [How to Run](#how-to-run)
- [Testing](#testing)
- [Production Notes](#production-notes)
- [Security Notes](#security-notes)

---

## API Documentation

The project includes built-in API documentation for convenient endpoint browsing and testing.

### Available Links

- Swagger UI: `http://127.0.0.1:8000/api/v1/schema/swagger/`
- Redoc: `http://127.0.0.1:8000/api/v1/schema/redoc/`
- OpenAPI Schema: `http://127.0.0.1:8000/api/v1/schema/`

These pages allow you to:
- explore available endpoints
- check request and response schemas
- test API requests in the browser

---

## Authentication

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

### Authorization Header

For protected endpoints, send:

```http
Authorization: Bearer <access_token>
```

---

### Logout

`POST /api/v1/users/logout/`

Headers:

```http
Authorization: Bearer <access_token>
```

Body:

```json
{
  "refresh": "your_refresh_token"
}
```

### How Logout Works

- Logout blacklists the refresh token
- After logout:
  - refresh token can no longer be used
  - an access token remains valid until it expires

### Important

- Access token lifetime is limited, for example 5 minutes
- After access token expiration, the user must log in again or refresh the token
- This is standard JWT behavior

---

## Users and Roles

### Implemented

- custom `User` model
- email-based authentication without username
- `is_blocked` field for user blocking

### Available Roles

- `user`
- `specialist`
- `moderator`
- `admin`

### Registration

During registration (`POST /api/v1/users/register/`), user must choose a role.

Available roles during registration:
- `user`
- `specialist`

Other roles (`moderator`, `admin`) cannot be assigned during registration.

Example request:

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123",
  "confirm_password": "StrongPassword123",
  "role": "specialist"
}
```

### Registration Flow

#### If role = `user`

1. Register
2. Create profile:

```http
POST /api/v1/profiles/user-profiles/
```

#### If role = `specialist`

1. Register
2. Create specialist profile:

```http
POST /api/v1/profiles/specialist-profiles/
```

3. Upload documents:

```http
POST /api/v1/profiles/documents/
```

---

## Access Control

Custom permissions are used:
- `IsAdminOrModerator`
- `IsOwnerOrStaff`

Role-based access is implemented in `UserViewSet`.

Only moderator/admin can:
- change roles
- block users
- delete users

Blocked user:
- cannot login
- cannot access protected endpoints

---

## API Endpoints

### Users

Main endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/users/list/` | List users, admin/moderator only |
| `GET` | `/api/v1/users/list/{id}/` | User details |
| `POST` | `/api/v1/users/register/` | Create user |
| `POST` | `/api/v1/users/login/` | Authorize user |
| `POST` | `/api/v1/users/logout/` | Logout and blacklist refresh token |
| `POST` | `/api/v1/users/password-reset/` | Request password reset |
| `POST` | `/api/v1/users/password-reset/confirm/` | Confirm password reset |
| `DELETE` | `/api/v1/users/list/{id}/` | Delete user |
| `POST` | `/api/v1/token/verify/` | Verify token |
| `POST` | `/api/v1/token/refresh/` | Refresh token |

Custom endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/users/list/{id}/block/` | Block user |
| `POST` | `/api/v1/users/list/{id}/change_role/` | Change role |
| `GET` | `/api/v1/users/list/me/` | Current user |

---

## Profiles and Documents

### Profiles

- profile management for users
- separate specialist profiles
- document management for specialist profiles
- CRUD endpoints for profiles and specialist profiles
- document upload and deletion endpoints

### Profile Changes

- `user` field is no longer selectable in API forms
- It is automatically assigned using authenticated user:

```python
serializer.save(user=request.user)
```

- In responses, user is shown as email:

```python
user_email = serializers.EmailField(source="user.email", read_only=True)
```

### Documents Changes

- `specialist` field is no longer selectable
- It is automatically assigned:

```python
serializer.save(specialist=user.specialist_profile)
```

- Displayed as email:

```python
specialist = serializers.EmailField(source="specialist.user.email", read_only=True)
```

### Document Upload Rules

- Only users with role `specialist` can upload documents
- Specialist must have a profile before uploading documents

### Security Improvements

- Cannot create profile for another user
- Cannot assign document to another specialist
- Ownership is enforced via `request.user`
- Related fields are read-only

---

### API Endpoints: Profiles

#### User Profiles

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/profiles/user-profiles/` | List profiles |
| `POST` | `/api/v1/profiles/user-profiles/` | Create profile |
| `GET` | `/api/v1/profiles/user-profiles/{id}/` | Retrieve profile details |
| `PUT` | `/api/v1/profiles/user-profiles/{id}/` | Update profile |
| `PATCH` | `/api/v1/profiles/user-profiles/{id}/` | Partially update profile |
| `DELETE` | `/api/v1/profiles/user-profiles/{id}/` | Delete profile |

#### Specialist Profiles

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/profiles/specialist-profiles/` | List specialist profiles |
| `POST` | `/api/v1/profiles/specialist-profiles/` | Create specialist profile |
| `GET` | `/api/v1/profiles/specialist-profiles/{id}/` | Retrieve specialist profile details |
| `PUT` | `/api/v1/profiles/specialist-profiles/{id}/` | Update specialist profile |
| `PATCH` | `/api/v1/profiles/specialist-profiles/{id}/` | Partially update specialist profile |
| `DELETE` | `/api/v1/profiles/specialist-profiles/{id}/` | Delete specialist profile |

#### Documents

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/profiles/documents/` | List documents |
| `POST` | `/api/v1/profiles/documents/` | Upload document |
| `GET` | `/api/v1/profiles/documents/{id}/` | Retrieve document details |
| `PATCH` | `/api/v1/profiles/documents/{id}/` | Partially update document |
| `DELETE` | `/api/v1/profiles/documents/{id}/` | Delete a document |

---

# Events App

## Overview

The Events app provides functionality for:
- event categories with images
- events with up to 6 images
- event description limited to 300 characters
- event likes
- comments under events
- comment likes
- displaying commentator avatar
- displaying commentator full name
- displaying comment creation time
- role-based event creation

---

## Events Permissions

### View Events

Everyone can view events.

### Create Events

Only the following users can create events:
- authenticated users with `specialist_profile`
- admin users with `is_staff=True`

Regular users without a specialist profile cannot create events.

### Edit/Delete Events

Only the event author can edit or delete their own event.

### Categories

Category permissions depend on the current `CategoryViewSet` configuration:
- if `IsAuthenticatedOrReadOnly` is used, authenticated users can create/edit/delete categories
- if `IsAdminUser` is used, only admins can create/edit/delete categories

Recommended production option:

```python
from rest_framework.permissions import IsAdminUser

permission_classes = [IsAdminUser]
```

### Likes and Comments

Only authenticated users can:
- like/unlike events
- create comments
- like/unlike comments

---

## Events Models

### Category

Fields:
- `name`
- `image`

Purpose:
- stores event category name and category photo

---

### Event

Fields:
- `title`
- `description`
- `category`
- `author`
- `created_at`
- `updated_at`

Rules:
- `description` has max length of 300 characters
- `author` is assigned automatically from `request.user`
- event can have up to 6 images

Computed fields:
- `likes_count`
- `comments_count`

---

### EventImage

Fields:
- `event`
- `image`

Rules:
- one event can have multiple images
- maximum allowed images per event: 6

---

### EventLike

Fields:
- `user`
- `event`

Rules:
- one user can like one event only once
- repeated like request works as toggle:
  - first request adds like
  - second request removes like

Recommended model string representation:

```python
def __str__(self):
    profile = getattr(self.user, "profile", None)
    specialist = getattr(self.user, "specialist_profile", None)

    if profile:
        name = f"{profile.first_name} {profile.last_name}".strip()
    elif specialist:
        name = f"{specialist.first_name} {specialist.last_name}".strip()
    else:
        name = self.user.email

    return f"{name} liked {self.event.title}"
```

---

### Comment

Fields:
- `event`
- `user`
- `text`
- `created_at`
- `updated_at`

Rules:
- comment is attached to a specific event
- `user` is assigned automatically from `request.user`

---

### CommentLike

Fields:
- `user`
- `comment`

Rules:
- one user can like one comment only once
- repeated like request works as toggle:
  - first request adds like
  - second request removes like

Recommended model string representation:

```python
def __str__(self):
    return f"{self.user} likes comment {self.comment.id}"
```

---

## Events API Endpoints

### Event Categories

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/events/categories/` | List event categories | Public |
| `POST` | `/api/v1/events/categories/` | Create event category | Auth/Admin, depending on permission |
| `GET` | `/api/v1/events/categories/{id}/` | Retrieve event category | Public |
| `PUT` | `/api/v1/events/categories/{id}/` | Update event category | Auth/Admin, depending on permission |
| `PATCH` | `/api/v1/events/categories/{id}/` | Partially update event category | Auth/Admin, depending on permission |
| `DELETE` | `/api/v1/events/categories/{id}/` | Delete event category | Auth/Admin, depending on permission |

---

### Events

| Method | Endpoint                        | Description               | Auth |
|---|---------------------------------|---------------------------|---|
| `GET` | `/api/v1/events/`               | List events               | Public |
| `POST` | `/api/v1/events/`               | Create event              | Specialist/Admin |
| `POST` | `/api/v1/events/{id}/register/` | To register for the event | Authenticated |
| `GET` | `/api/v1/events/{id}/`          | Retrieve event details    | Public |
| `PUT` | `/api/v1/events/{id}/`          | Update event              | Event author |
| `PATCH` | `/api/v1/events/{id}/`          | Partially update event    | Event author |
| `DELETE` | `/api/v1/events/{id}/`          | Delete event              | Event author |

---

### Event Likes

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/events/{id}/like/` | Like/unlike event | Authenticated |

Response examples:

```json
{
  "detail": "Event liked"
}
```

```json
{
  "detail": "Event unliked"
}
```

---

### Event Comments

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/events/{event_pk}/comments/` | List comments under event | Public |
| `POST` | `/api/v1/events/{event_pk}/comments/` | Create comment under event | Authenticated |
| `GET` | `/api/v1/events/{event_pk}/comments/{id}/` | Retrieve comment details | Public |
| `PUT` | `/api/v1/events/{event_pk}/comments/{id}/` | Fully update comment | Owner/Admin/Moderator |
| `PATCH` | `/api/v1/events/{event_pk}/comments/{id}/` | Partially update comment | Owner/Admin/Moderator |
| `DELETE` | `/api/v1/events/{event_pk}/comments/{id}/` | Delete comment | Owner/Admin/Moderator |

Example request:

```json
{
  "text": "Great event!"
}
```

Example response:

```json
{
  "id": 1,
  "event": 5,
  "user": 2,
  "user_full_name": "John Smith",
  "user_avatar": "/media/uploads/profiles/avatar.jpg",
  "text": "Great event!",
  "likes_count": 0,
  "created_at": "2026-04-29T12:00:00Z",
  "updated_at": "2026-04-29T12:00:00Z"
}
```

---

### Comment Likes

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/events/{event_pk}/comments/{id}/like/` | Like/unlike comment | Authenticated |

Response examples:

```json
{
  "detail": "Comment liked"
}
```

```json
{
  "detail": "Comment unliked"
}
```

---

## Events Request Examples

### Create Event With Images

Request type: `multipart/form-data`

Endpoint:

```http
POST /api/v1/events/
```

Headers:

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

Form data:

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | yes | Event title |
| `description` | string | yes | Max 300 characters |
| `category` | integer | yes | Category ID |
| `images` | file[] | no | Max 6 images |

Example form-data:

```text
title: Group therapy meeting
description: Short event description up to 300 characters.
category: 1
images: image1.jpg
images: image2.png
```

---

## Events Image Upload Rules

Recommended validation rules:
- maximum 6 images per event
- allowed image types:
  - JPEG
  - PNG
  - WEBP
- recommended maximum file size: 5 MB per image

Recommended validation helper:

```python
from PIL import Image

MAX_EVENT_IMAGES = 6
MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _validate_images_count(images):
    if len(images) > MAX_EVENT_IMAGES:
        return f"Maximum {MAX_EVENT_IMAGES} images allowed."
    return None


def _validate_image_type(image):
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        return "Only JPEG, PNG and WEBP images are allowed."
    return None


def _validate_image_size(image):
    if image.size > MAX_IMAGE_SIZE:
        return "Each image must be smaller than 5 MB."
    return None


def _validate_image_content(image):
    try:
        img = Image.open(image)
        img.verify()
    except Exception:
        return "Invalid image file."
    return None


def validate_event_images(images):
    if not images:
        return None

    error = _validate_images_count(images)
    if error:
        return error

    for image in images:
        for validator in (
            _validate_image_type,
            _validate_image_size,
            _validate_image_content,
        ):
            error = validator(image)
            if error:
                return error

    return None
```

Usage in `EventViewSet.create()`:

```python
images = request.FILES.getlist("images")

image_error = validate_event_images(images)
if image_error:
    return Response(
        {"images": image_error},
        status=status.HTTP_400_BAD_REQUEST,
    )
```

---

## Events Full Name Logic

User first name and last name are stored in profile models, not directly in the `User` model.

Full name should be resolved in this order:
1. `profile`
2. `specialist_profile`
3. fallback to `email`

Recommended helper:

```python
def get_user_full_name(user):
    profile = getattr(user, "profile", None)
    if profile:
        full_name = f"{profile.first_name} {profile.last_name}".strip()
        if full_name:
            return full_name

    specialist_profile = getattr(user, "specialist_profile", None)
    if specialist_profile:
        full_name = (
            f"{specialist_profile.first_name} "
            f"{specialist_profile.last_name}"
        ).strip()
        if full_name:
            return full_name

    return user.email
```

Recommended avatar helper:

```python
def get_user_avatar(user):
    profile = getattr(user, "profile", None)
    if profile and profile.avatar:
        return profile.avatar.url

    specialist_profile = getattr(user, "specialist_profile", None)
    if specialist_profile and specialist_profile.avatar:
        return specialist_profile.avatar.url

    return None
```

---

## Event Registration

The platform supports full event registration functionality with validation and ограничения.

### Model: EventRegistration

Each registration includes:

- full_name
- birth_date
- gender (based on Profile.Gender)
- phone (validated via `phonenumber_field`)
- email
- experience (enum):
  - parents
  - teacher
  - psychologist
  - trauma_pedagogy
  - social_worker
  - other
- eating_meat (boolean)
- is_agreed (GDPR / policy consent)

### Constraints

- Unique registration per event per email:
```python
UniqueConstraint(fields=["event", "email"])
```

### Relations

- Event → registrations (reverse FK)
- User → event_registrations (optional FK)

### Business Logic

- Limit participants via `Event.max_participants`
- Use `registrations_count` property for quick aggregation
- Validate:
  - unique email per event
  - consent (`is_agreed=True`)
  - phone format
- Allow both:
  - authenticated users
  - anonymous registrations

### API (typical flow)

#### Register for event

`POST /api/v1/events/{id}/register/`

Body:

```json
{
  "full_name": "John Doe",
  "birth_date": "1990-01-01",
  "gender": "male",
  "phone": "+380XXXXXXXXX",
  "email": "john@example.com",
  "experience": "teacher",
  "eating_meat": true,
  "is_agreed": true
}
```

#### Expected validations

- 400 if:
  - already registered
  - max participants reached
  - invalid phone/email
  - is_agreed = false

#### Response

```json
{
  "id": 1,
  "event": 10,
  "full_name": "John Doe",
  "email": "john@example.com"
}
```

### Notes

- Prefer service layer for registration logic (avoid fat serializers)
- Use atomic transactions when checking limits
- Add DB index on `(event, email)` for performance
- Consider soft limits / waiting list in future


## Events Performance Notes

Recommended queryset optimization:

```python
Event.objects.select_related(
  "author",
  "author__profile",
  "author__specialist_profile",
  "category",
  )
.prefetch_related(
  "images",
  "likes",
  "comments",
)
.order_by("-created_at")
```

For comments:

```python
Comment.objects.select_related(
    "event",
    "user",
).prefetch_related("likes")
```

---

## Events Filtering, Search and Sorting

### Overview

The Events API supports advanced filtering, searching, ordering, and pagination using `django-filter` and DRF built-in tools.

---

### Filtering

Filtering is implemented using `django-filter`.

#### Available Filters

| Parameter | Type | Description |
|---|---|---|
| `category` | integer | Filter by category ID |
| `author` | integer | Filter by author ID |
| `created_after` | date | Events created after given date |
| `created_before` | date | Events created before given date |

#### Examples

```http
GET /api/v1/events/?category=1
GET /api/v1/events/?author=5
GET /api/v1/events/?created_after=2026-05-01
GET /api/v1/events/?created_before=2026-04-01
```

---

### Search

Search is implemented using DRF `SearchFilter`.

#### Fields

- `title`
- `description`

#### Example

```http
GET /api/v1/events/?search=therapy
```

---

### Ordering

Ordering is implemented using DRF `OrderingFilter`.

#### Available Fields

- `created_at`

#### Examples

```http
GET /api/v1/events/?ordering=-created_at
GET /api/v1/events/?ordering=created_at
```

---

### Pagination

Pagination is enabled using DRF `PageNumberPagination`.

Default page size:

```text
10 items per page
```

#### Example

```http
GET /api/v1/events/?page=2
```

---

### Technical Implementation

Filtering is powered by:

- `DjangoFilterBackend`
- `SearchFilter`
- `OrderingFilter`

Configured in `EventViewSet`:

```python
filter_backends = [
    DjangoFilterBackend,
    SearchFilter,
    OrderingFilter,
]

filterset_class = EventFilter
search_fields = ["title", "description"]
ordering_fields = ["created_at"]
ordering = ["-created_at"]
```

---

### Important Notes

- Query parameters must not contain trailing `/`
- Example of incorrect request:

```http
GET /api/v1/events/?category=1/
```

- Correct request:

```http
GET /api/v1/events/?category=1
```

- If no records match filters, API returns:

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

---

### Performance Optimization

Recommended queryset optimization:

```python
Event.objects.select_related(
    "author",
    "author__profile",
    "author__specialist_profile",
    "category",
).prefetch_related(
    "images",
    "likes",
    "comments",
).order_by("-created_at")
```

# Scheduling App

### Overview

Specialists can create availability slots, and users can book appointments.  
Appointments are automatically marked as completed when their time has passed.

---

### Slots

- Slots are 1 hour long, starting on the hour or half-hour
- Only verified specialists can create slots
- Unbooked future slots are visible to all users (for calendar display)

#### Endpoints

- `GET api/v1/scheduling/slots/` — list available slots (filter by `?specialist=<id>`)
- `POST api/v1/scheduling/slots/bulk_create/` — create multiple slots (verified specialist only)
- `DELETE api/v1/scheduling/slots/<id>/` — delete an unbooked slot (owner and admin)

#### Bulk create example

```json
{
  "start_times": [
    "2025-06-01T10:00:00Z",
    "2025-06-01T10:30:00Z"
  ]
}
```

---

### Appointments

- Only users with a profile can book appointments
- Specialists can reschedule or cancel appointments
- Appointments are automatically marked as `completed` once the slot time has passed

#### Statuses

- `confirmed` — active upcoming appointment
- `cancelled` — cancelled by specialist or admin
- `completed` — past appointment, auto-marked by the system

#### Endpoints

- `POST api/v1/scheduling/appointments/` — book an appointment (user only)
- `GET api/v1/scheduling/appointments/` — list confirmed appointments
- `GET api/v1/scheduling/appointments/<id>/` — retrieve appointment details
- `PATCH api/v1/scheduling/appointments/<id>/reschedule/` — reschedule (specialist and admin only)
- `PATCH api/v1/scheduling/appointments/<id>/cancel/` — cancel (specialist and admin only)
- `GET api/v1/scheduling/appointments/completed/` — list completed appointments

#### Sorting

Both `/appointments/` and `/appointments/completed/` support sorting via query parameters:

- `sort_field` — field to sort by, currently only `date` is supported
- `sort_direction` — `asc` or `desc`; defaults to `asc` for confirmed, `desc` for completed

Example:
```
GET /api/v1/scheduling/appointments/?sort_field=date&sort_direction=desc
GET /api/v1/scheduling/appointments/completed/?sort_direction=asc
```

---

### Date Filtering

Appointments can be filtered by date using the `date` query parameter.

Format: `YYYY-MM-DD`

Example:

```
GET /api/v1/scheduling/appointments/?date=2026-06-10
GET /api/v1/scheduling/appointments/completed/?date=2026-06-10
```

This returns all appointments (confirmed or completed) for the selected day.  
Sorting and other filters (such as `user` for specialists) can be used together with the date filter.

Example:

```
GET /api/v1/scheduling/appointments/?user=42&date=2026-06-10
GET /api/v1/scheduling/appointments/?date=2026-06-10&sort_direction=desc
```

---

### Role-based visibility

- **User** — own appointments only
- **Specialist** — their own appointments; can filter by `?user=<id>`
- **Admin / Moderator** — all appointments

---

### Book again

Completed appointments (user view) include a `book_again_url` field:

```json
{
  "book_again_url": "/api/v1/scheduling/slots/?specialist=3"
}
```

This URL returns the specialist's future available slots so the user can rebook.

---

### Celery task — cleanup

A periodic task deletes unbooked past slots to keep the database clean.

---

# Education Materials App

## Overview

The Education Materials app provides functionality for:
- educational articles with rich text sections
- educational video materials
- likes for articles and videos
- comments for articles and videos
- comment likes
- favorites system using GenericForeignKey
- role-based content management
- draft/published moderation flow
- automatic slug generation
- automatic counters update via Django signals

---

## Education Materials Permissions

### View Content

- Everyone can view published articles and videos
- Draft materials are visible only to:
  - author
  - admin
  - moderator

### Create Content

Only:
- `specialist`
- `admin`
- `moderator`

can create:
- articles
- video materials

### Edit/Delete Content

Only:
- content author
- admin
- moderator

can update or delete materials.

### Likes / Favorites / Comments

Only authenticated users can:
- like/unlike materials
- add/remove favorites
- create comments
- like/unlike comments
- edit own comments

---

## Article Model

### Main Fields

| Field | Type | Description |
|---|---|---|
| `author` | FK(User) | Article author |
| `title` | CharField | Article title |
| `slug` | SlugField | Auto-generated unique slug |
| `cover_image` | ImageField | Article preview image |
| `status` | CharField | draft / published |
| `published_at` | DateTimeField | Publication datetime |
| `likes_count` | PositiveIntegerField | Cached likes count |
| `comments_count` | PositiveIntegerField | Cached comments count |
| `favorites_count` | PositiveIntegerField | Cached favorites count |

### Statuses

```python
class Status(models.TextChoices):
    DRAFT = "draft"
    PUBLISHED = "published"
```

### Slug Generation

Slug is generated automatically from article title.

Example:

```text
Mental Health Tips -> mental-health-tips
```

Implemented via:

```python
generate_unique_slug()
```

---

## Article Sections

Articles support multiple structured sections.

### ArticleSection Fields

| Field | Description |
|---|---|
| `article` | Related article |
| `title` | Section title |
| `slug` | Auto-generated section slug |
| `content` | CKEditor rich text |
| `order` | Display ordering |

### Features

- sections are ordered by `order`
- section slug is generated automatically
- suitable for frontend anchor navigation

Example:

```text
/article/my-article/#introduction
```

---

### Main Fields

| Field | Type |
|---|---|
| `author` | FK(User) |
| `title` | CharField |
| `slug` | SlugField |
| `short_description` | TextField |
| `content` | CKEditor5Field |
| `video_file` | FileField |
| `status` | draft/published |
| `published_at` | DateTimeField |
| `likes_count` | PositiveIntegerField |
| `comments_count` | PositiveIntegerField |
| `favorites_count` | PositiveIntegerField |


### Video Upload Validation

Allowed formats:
- mp4
- mov
- avi
- mkv
- webm

Implemented using:

```python
FileExtensionValidator
```

---

## Favorites System

Favorites are implemented using Django Generic Relations.

Supported content:
- Article
- VideoMaterial

### Favorite Model

| Field | Description |
|---|---|
| `user` | User who added favorite |
| `content_type` | Django content type |
| `object_id` | Related object id |
| `content_object` | Generic relation |

This allows one universal favorites table for multiple models.

---

## Signals

The app uses Django signals for automatic counters synchronization.

Implemented counters:
- article likes
- article comments
- article favorites
- video likes
- video comments
- video favorites

Signals:
- `post_save`
- `post_delete`

Example:

```python
@receiver(post_save, sender=ArticleLike)
def article_like_created(sender, instance, **kwargs):
    update_article_likes_count(instance.article)
```

---

## Education Materials API Endpoints

### Articles

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/education-materials/articles/` | List published articles | Public |
| `POST` | `/api/v1/education-materials/articles/` | Create article | Specialist/Admin/Moderator |
| `GET` | `/api/v1/education-materials/articles/{slug}/` | Retrieve article details | Public |
| `PATCH` | `/api/v1/education-materials/articles/{slug}/` | Partially update article | Author/Admin/Moderator |
| `DELETE` | `/api/v1/education-materials/articles/{slug}/` | Delete article | Author/Admin/Moderator |

---

### Article Likes

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/education-materials/articles/{slug}/like/` | Like/unlike article |

Response:

```json
{
  "detail": "Article liked",
  "likes_count": 1
}
```

---

### Article Favorites

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/education-materials/articles/{slug}/favorite/` | Add/remove favorite |

---

### Article Comments

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/education-materials/articles/{slug}/comments/` | List comments |
| `POST` | `/api/v1/education-materials/articles/{slug}/comments/` | Create comment |

---

### Article Comment CRUD

| Method | Endpoint | Description |
|---|---|---|
| `PATCH` | `/api/v1/education-materials/article-comments/{id}/` | Edit comment |
| `DELETE` | `/api/v1/education-materials/article-comments/{id}/` | Delete comment |

---

### Article Comment Likes

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/education-materials/article-comments/{id}/like/` | Like/unlike article comment |

---

## Video Materials API

### Videos

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/education-materials/videos/` | List videos | Public |
| `POST` | `/api/v1/education-materials/videos/` | Create video | Specialist/Admin/Moderator |
| `GET` | `/api/v1/education-materials/videos/{slug}/` | Retrieve video details | Public |
| `PATCH` | `/api/v1/education-materials/videos/{slug}/` | Partially update video | Author/Admin/Moderator |
| `DELETE` | `/api/v1/education-materials/videos/{slug}/` | Delete video | Author/Admin/Moderator |

---

### Video Likes

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/education-materials/videos/{slug}/like/` | Like/unlike video |

---

### Video Favorites

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/education-materials/videos/{slug}/favorite/` | Add/remove favorite |

---

### Video Comments

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/education-materials/videos/{slug}/comments/` | List comments |
| `POST` | `/api/v1/education-materials/videos/{slug}/comments/` | Create comment |

---

### Video Comment CRUD

| Method | Endpoint | Description |
|---|---|---|
| `PATCH` | `/api/v1/education-materials/video-comments/{id}/` | Edit video comment |
| `DELETE` | `/api/v1/education-materials/video-comments/{id}/` | Delete video comment |

---

### Video Comment Likes

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/education-materials/video-comments/{id}/like/` | Like/unlike video comment |

---

## Queryset Optimization

Recommended queryset optimization:

```python
Article.objects.select_related(
    "author",
).prefetch_related(
    "sections",
)
```

```python
VideoMaterial.objects.select_related(
    "author",
)
```

---

## Admin Panel Improvements

Implemented admin improvements:
- read-only counters
- automatic slug generation
- truncated long comments
- disabled manual editing for likes/favorites
- custom verbose names
- custom object string representation
- inline article sections


# Password Reset (Django + DRF + Celery)

## Overview

Password reset functionality is implemented using:
- Django built-in token generator
- DRF endpoints
- Celery for async email sending
- Redis as broker

Flow:
1. User sends email
2. Backend generates uid + token
3. Sends reset link via Celery task
4. User opens link
5. User sends new password
6. Password is updated

---

## `.env` Configuration

Add the following variables:

```env
FRONTEND_URL=http://localhost:5173
# for backend-only testing:
# FRONTEND_URL=http://127.0.0.1:8000/api/v1/users

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### `EMAIL_HOST_PASSWORD` for Google

This is not your Gmail password.

You must generate an App Password:

1. Go to Google Account -> Security
2. Enable 2FA
3. Go to: `https://myaccount.google.com/apppasswords`
4. Generate password for "Mail"
5. Use it as `EMAIL_HOST_PASSWORD`

---

## Redis (Celery) via Docker

To run Redis locally for Celery, use Docker.

### Run Redis Container

```bash
docker run -d -p 6379:6379 --name redis redis
```

### Check if Container Is Running

```bash
docker ps
```

### Stop Redis

```bash
docker stop redis
```

### Start Again

```bash
docker start redis
```

---

## Celery Start

Open a new terminal:

```bash
cd backend
celery -A config worker -l info
```

For Windows:

```bash
celery -A config worker -l info -P solo
```

### Notes

- Redis must be running before starting Celery
- Default port: `6379`
- Broker URL must match `.env`:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
```

---

## Password Reset Endpoints

### Request Reset

`POST /api/v1/users/password-reset/`

Request:

```json
{
  "email": "user@example.com"
}
```

Response:

```json
{
  "detail": "If this email exists, reset link was generated."
}
```

### Reset Password: GET for Testing

`GET /api/v1/users/password-reset/confirm/?uid=...&token=...`

### Confirm Reset

`POST /api/v1/users/password-reset/confirm/`

Request:

```json
{
  "uid": "...",
  "token": "...",
  "password": "NewPass123!",
  "confirm_password": "NewPass123!"
}
```

---

# Google OAuth Login

## What Is Implemented

Google OAuth authentication is implemented using:
- `django-allauth`
- `dj-rest-auth`
- JWT with SimpleJWT

Custom logic:
- blocking login for users with `is_blocked=True`
- auto-connecting existing users by email
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

### Authorized Redirect URIs

For development with React:

```text
http://localhost:5173/auth/google/callback
```

For backend-only testing:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
```

---

## Django Settings

Already configured:

```python
REST_USE_JWT = True
```

Also configured:
- JWT enabled
- allauth and Google provider

See `settings.py`.

---

## Google Login Endpoint

`POST /api/v1/users/google/`

Request:

```json
{
  "access_token": "your_google_access_token"
}
```

Response:

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

## Flow: React + Backend

1. React starts Google OAuth
2. Google redirects to:

```text
http://localhost:5173/auth/google/callback
```

3. React extracts `access_token`
4. React sends POST request to backend:

```http
POST /api/v1/users/google/
```

5. Backend:
   - verifies token via Google
   - creates or gets user
   - returns JWT tokens

6. React:
   - stores token
   - sends Authorization header in future requests

---

## Media Support

- Added `MEDIA_ROOT` and `MEDIA_URL` to enable serving uploaded files
- Added upload paths for:
  - profile avatars
  - specialist avatars
  - specialist documents
  - event category images
  - event images

Uploaded files are stored under the `uploads/` directory with automatically generated filenames.

---

## Project Structure (Main Parts)

```text
teamproject225-backend/
├── .github/workflows/
│   ├── backend-ci.yml
│   └── python-check.yml
├── backend/
│   ├── __init__.py
│   ├── .env.example
│   ├── config/                  # Django settings, urls, asgi, wsgi, celery
│   ├── users/
│   │   ├── api/
│   │   │   └── v1/              # API versioning
│   │   │       ├── permissions.py
│   │   │       ├── serializers.py
│   │   │       ├── tasks.py
│   │   │       ├── validators.py
│   │   │       ├── urls.py
│   │   │       └── views.py
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py             # admin configuration
│   │   ├── apps.py
│   │   ├── models.py            # User model
│   │   ├── selectors.py         # data access layer
│   │   ├── services.py          # business logic
│   │   └── social_adapter.py    # OAuth logic
│   ├── profiles/
│   │   ├── migrations/
│   │   ├── tests/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── events/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── permissions.py
│   │   │       ├── serializers.py
│   │   │       ├── urls.py
│   │   │       └── views.py
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── utils.py
│   │   ├── services.py
│   │   └── models.py
│   ├── scheduling/
│   │  ├── migrations/
│   │  ├── tests/
│   │  ├── __init__.py
│   │  ├── admin.py
│   │  ├── apps.py
│   │  ├── models.py
│   │  ├── serializers.py
│   │  ├── services.py
│   │  ├── tasks.py
│   │  ├── urls.py
│   │  └── views.py
│   ├── __init__.py
│   ├── manage.py
│   ├── .env.example
│   └── requirements.txt
├── .dockerignore
├── .gitignore
├── conftest.py
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## How to Run

Create a `.env` file in the `backend/` directory and add:

```env
#Django
SECRET_KEY=SECRET_KEY

#Email
FRONTEND_URL=FRONTEND_URL

EMAIL_HOST=EMAIL_HOST
EMAIL_PORT=EMAIL_PORT
EMAIL_HOST_USER=EMAIL_HOST_USER
EMAIL_HOST_PASSWORD=EMAIL_HOST_PASSWORD

CELERY_BROKER_URL=CELERY_BROKER_URL
CELERY_RESULT_BACKEND=CELERY_RESULT_BACKEND

#Postgres
POSTGRES_DB=POSTGRES_DB
POSTGRES_USER=POSTGRES_USER
POSTGRES_PASSWORD=POSTGRES_PASSWORD
POSTGRES_HOST=POSTGRES_HOST
POSTGRES_PORT=POSTGRES_PORT
```

You can generate a Django secret key using:
- `https://djecrety.ir/`
- or via command:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Local Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## Testing

The project uses pytest with pytest-django for backend testing.

### Configuration
Test settings are defined in pyproject.toml.  
A shared conftest.py at the project root provides common fixtures used across all apps.

### Running Tests

```bash
# All tests
pytest

# Specific app
pytest profiles/tests/

# With output
pytest -v
```

---

## Production Notes

- Use Celery + Redis
- Use HTTPS
- Do not expose user existence during password reset
- Use strong password validation
- Store secrets only in environment variables
- Do not commit `.env`
- Configure allowed hosts and CORS for production frontend
- Use proper media storage for production deployments

---

## Security Notes

- Blocked users cannot:
  - login
  - access protected endpoints
- All protected requests are checked with custom permissions
- The minimum password length is 8 characters
- The maximum password length is 128 characters
- Event author is assigned automatically from `request.user`
- Profile/document ownership is enforced via `request.user`
- Related fields are read-only where users should not manually assign ownership


---
