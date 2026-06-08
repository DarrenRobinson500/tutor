# Tutor Platform

A tutoring management platform with scheduling, bookings, SMS, AI question generation, and student progress tracking.

## Tech Stack

| Layer | Detail |
|-------|--------|
| Backend | Django 4.2, Django REST Framework |
| Auth | JWT (djangorestframework-simplejwt) — admin creates accounts via Django admin |
| Database | PostgreSQL (via Django ORM), SQLite fallback for local dev |
| Task queue | Celery 5 with Redis broker — worker + beat processes |
| Beat scheduler | django-celery-beat — schedules managed via Django admin |
| Frontend | React 19, TypeScript, Create React App |
| API style | REST / JSON — frontend uses JWT Authorization header |
| CORS | django-cors-headers |

---

## Project Structure

```
tutor/
  backend/
    manage.py
    config/               # Django project config (settings, urls, wsgi, celery)
    backend/              # Main Django app (models, views, serializers, tasks)
    requirements.txt
  frontend/
    src/
    public/
    package.json
  .env                    # Local dev env vars (gitignored)
  .env.example            # Template — copy and fill in
  README.md
```

---

## Backend Setup

### Prerequisites
- Python 3.9+
- PostgreSQL running locally (or leave `DATABASE_URL` blank to use SQLite)
- Redis running locally (`redis-server`)

### Steps

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and populate env file (already created at project root)
# Edit tutor/.env with your local values

# Run migrations (includes django_celery_beat tables)
python manage.py migrate

# Create admin superuser
python manage.py createsuperuser

# Start Django dev server
python manage.py runserver
```

Django is now running at **http://localhost:8000**

---

## Celery Local Dev Setup

Redis must be running before starting Celery. On Windows, use WSL or the Windows Redis installer.

```bash
# macOS
brew install redis && redis-server

# Ubuntu / WSL
sudo apt install redis-server && redis-server
```

Three terminal sessions are required:

### Terminal 1 — Django dev server
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

### Terminal 2 — Celery worker
```bash
cd backend
source venv/bin/activate
celery -A config worker --loglevel=info
```

### Terminal 3 — Celery Beat (scheduler)
```bash
cd backend
source venv/bin/activate
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Configuring Periodic Tasks
Schedules are managed via Django admin (not hardcoded). After first `migrate`, log into **http://localhost:8000/admin** and add the following periodic tasks under **Periodic Tasks**:

| Task name | Schedule | Description |
|-----------|----------|-------------|
| `backend.tasks.run_sms_jobs` | Every 5 minutes | Process outbound SMS queue |
| `backend.tasks.create_post_session_jobs` | Every 30 minutes | Create post-session review jobs |
| `backend.tasks.create_weekly_session_jobs` | Every 24 hours | Ensure weekly booking jobs exist |
| `backend.tasks.record_weekly_progress_snapshots` | Sunday 9 pm AEST | Snapshot student progress |

---

## Frontend Setup

### Prerequisites
- Node.js 18+

### Steps

```bash
cd frontend
npm install

# Start dev server
npm start
```

The React dev server runs at **http://localhost:3000**. API calls proxy to Django at **http://localhost:8000**.

---

## Creating User Accounts

User accounts are created by an admin via Django admin:

1. Go to **http://localhost:8000/admin**
2. Log in with your superuser credentials
3. Navigate to **Users** and click **Add User**
4. Set username, password, and `role` field (tutor / student / admin / parent / distributor / teacher)

---

## Environment Variables

| Variable | Description | Local default |
|----------|-------------|---------------|
| `SECRET_KEY` | Django secret key | `dev-secret-key-change-before-deploying` |
| `DATABASE_URL` | PostgreSQL connection URL | Empty → uses SQLite |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins (production) | `http://localhost:3000` |
| `DEBUG` | Enable debug mode | `True` |
| `FRONTEND_URL` | Frontend URL for CORS (production) | — |
| `CUSTOM_DOMAIN` | Custom domain for ALLOWED_HOSTS | — |
| `EMAIL_HOST_USER` | SMTP email address | — |
| `EMAIL_HOST_PASSWORD` | SMTP password | — |
| `CLICKSEND_USERNAME` | ClickSend API username | — |
| `CLICKSEND_API_KEY` | ClickSend API key | — |
| `CLICKSEND_FROM_NUMBER` | SMS sender number | — |
