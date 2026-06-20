# Study Group Finder — FastAPI Backend

Built with **FastAPI** + **SQLAlchemy (async)** + **Supabase PostgreSQL**

---

## Quick Start

### 1. Clone & Install

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and fill in:
- Replace `[YOUR-PASSWORD]` in `DATABASE_URL` with your actual Supabase DB password
- Set a strong `SECRET_KEY` and `JWT_SECRET_KEY`
- Add your email credentials for verification emails

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@db.fuguskpcemwhwibqyshd.supabase.co:5432/postgres
SECRET_KEY=your-strong-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
```

### 3. Create the Database Tables

```bash
python -m alembic upgrade head
```

Or let the app auto-create tables on first run (already configured in `lifespan`).

### 4. Run the Server

```bash
uvicorn app.main:app --reload
```

App is now running at:
- **API:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Project Structure

```
study_group_finder/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── core/
│   │   ├── config.py            # All settings from .env
│   │   ├── database.py          # Supabase connection + session
│   │   └── security.py          # JWT auth + password hashing
│   ├── models/
│   │   └── student.py           # All SQLAlchemy models (DB tables)
│   ├── schemas/
│   │   └── schemas.py           # Pydantic schemas (request/response)
│   └── routers/
│       ├── auth.py              # Register, Login, Verify Email, Reset Password
│       ├── students.py          # Profile, Course Enrollment
│       ├── groups.py            # Full group CRUD + join/leave/members
│       ├── other.py             # Courses, Sessions, Resources, Notifications
│       ├── chat.py              # WebSocket real-time chat
│       └── matching.py          # Smart group suggestions
├── tests/
│   └── test_api.py              # Pytest test suite
├── alembic/
│   └── env.py                   # Migration config
├── requirements.txt
└── .env.example
```

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register` | Register student | No |
| POST | `/api/v1/auth/login` | Login + get tokens | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | No |
| POST | `/api/v1/auth/verify-email` | Verify email token | No |
| POST | `/api/v1/auth/forgot-password` | Request password reset | No |
| POST | `/api/v1/auth/reset-password` | Set new password | No |
| GET  | `/api/v1/auth/me` | Get current user | Yes |
| GET  | `/api/v1/students/profile` | Get profile | Yes |
| PUT  | `/api/v1/students/profile` | Update profile | Yes |
| GET  | `/api/v1/students/my-courses` | List enrolled courses | Yes |
| POST | `/api/v1/students/enroll/{course_id}` | Enroll in course | Yes |
| GET  | `/api/v1/groups/` | List groups | Yes |
| POST | `/api/v1/groups/` | Create group | Yes |
| GET  | `/api/v1/groups/{id}` | Group details + members | Yes |
| PUT  | `/api/v1/groups/{id}` | Update group | Yes (admin) |
| DELETE | `/api/v1/groups/{id}` | Delete group | Yes (creator) |
| POST | `/api/v1/groups/{id}/join` | Join group | Yes |
| POST | `/api/v1/groups/{id}/leave` | Leave group | Yes |
| POST | `/api/v1/groups/{id}/members` | Add member | Yes (admin) |
| DELETE | `/api/v1/groups/{id}/members/{student_id}` | Remove member | Yes (admin) |
| PUT  | `/api/v1/groups/{id}/members/role` | Update member role | Yes (admin) |
| GET  | `/api/v1/courses/` | List courses | Yes |
| POST | `/api/v1/courses/` | Create course | Yes (staff) |
| POST | `/api/v1/sessions/` | Create study session | Yes |
| GET  | `/api/v1/sessions/group/{id}` | List group sessions | Yes |
| GET  | `/api/v1/resources/group/{id}` | List group resources | Yes |
| POST | `/api/v1/resources/group/{id}` | Upload resource | Yes |
| GET  | `/api/v1/notifications/` | Get notifications | Yes |
| PUT  | `/api/v1/notifications/{id}/read` | Mark as read | Yes |
| GET  | `/api/v1/matching/suggestions` | Get group suggestions | Yes |
| WS   | `/api/v1/chat/{group_id}?token=...` | Real-time group chat | Token |

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx aiosqlite
pytest tests/ -v
```

---

## Deliverables Timeline

| Week | Tasks |
|------|-------|
| 1–2 | ✅ Project setup, auth (register/login/logout), JWT, email verify, profile API |
| 3–4 | ✅ Courses API, enrollment, password reset, user CRUD |
| 5–6 | ✅ Groups API, resources, sessions, dashboard endpoint |
| 7–8 | ✅ WebSocket chat, notifications, smart matching, tests |
